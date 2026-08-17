#!/usr/bin/env python3
"""Serve interactive readers with a subscription-backed Codex tutor.

The browser talks only to this loopback HTTP server. The server launches
``codex app-server`` over stdio and reuses the user's existing ChatGPT login,
so no API key or account token is exposed to the reader HTML.
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse


MAX_REQUEST_BYTES = 512_000
RPC_TIMEOUT_SECONDS = 120
ALLOWED_ORIGINS = {
    "null",
    "http://127.0.0.1:8765",
    "http://localhost:8765",
}

TUTOR_INSTRUCTIONS = """你是科研论文的学习助手。默认用清晰、紧凑的中文回答，并在首次出现时保留重要英文术语。

回答规则：
1. 优先使用请求里提供的论文与当前 Figure 上下文。
2. 严格区分“本文提供的证据”和“一般科学知识”。不要把常识伪装成论文结论。
3. 涉及本文时，引用可核对的位置，例如 Figure 编号、Question、Observation、Claim、Limitation 或 Validation audit。
4. 上下文没有答案时，明确说“当前阅读器内容没有说明”，然后再给一般解释。
5. 不夸大因果关系、外部有效性或样本独立性。留意 donor、condition、biological replicate、technical replicate 和数据泄漏。
6. 对术语问题，依次给出：一句话解释、本文语境、一个具体例子。对图表问题，依次解释数据来源、读图方法、观察、作者主张和局限性。
7. 不虚构页码、数值、实验步骤或统计结果。
8. 这是只读教学对话。只回答问题，不运行命令、不修改文件、不调用工具，也不要制定执行计划。"""


class CodexBridgeError(RuntimeError):
    """A user-displayable problem from the local Codex bridge."""


class ObsidianBridge:
    """Append evidence-aware reader captures to one local Obsidian vault."""

    def __init__(self, config_path: Path | None) -> None:
        self.config_path = config_path
        self.lock = threading.Lock()
        self.vault: Path | None = None
        self.papers_dir = "Research/Papers"
        self.error: str | None = None
        self._load_config()

    def _load_config(self) -> None:
        if self.config_path is None:
            self.error = "未提供 Obsidian 配置"
            return
        try:
            config = json.loads(self.config_path.expanduser().read_text(encoding="utf-8"))
            vault = Path(str(config.get("vault", ""))).expanduser().resolve()
            papers_dir = str(config.get("papers_dir", self.papers_dir)).strip().strip("/")
            if not vault.is_dir() or not (vault / ".obsidian").is_dir():
                raise ValueError("配置的路径不是有效的 Obsidian Vault")
            if not papers_dir:
                raise ValueError("papers_dir 不能为空")
            target = (vault / papers_dir).resolve()
            if not target.is_relative_to(vault):
                raise ValueError("papers_dir 必须位于 Vault 内")
            self.vault = vault
            self.papers_dir = papers_dir
            self.error = None
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.error = str(error)

    def status(self) -> dict[str, Any]:
        return {
            "ok": self.vault is not None and self.error is None,
            "configured": self.vault is not None and self.error is None,
            "vaultName": self.vault.name if self.vault else None,
            "papersDir": self.papers_dir,
            "error": self.error,
        }

    @staticmethod
    def _clean(value: Any, limit: int) -> str:
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value or ""))[:limit].strip()

    @staticmethod
    def _filename(title: str, authors: str, year: str) -> str:
        first_author = authors.split(",", 1)[0].strip().split()
        surname = first_author[-1] if first_author else "Paper"
        short_title = re.sub(r"[^\w\- ]+", "", title, flags=re.UNICODE)
        short_title = re.sub(r"\s+", " ", short_title).strip()[:72].rstrip()
        name = f"{surname} {year} - {short_title}".strip(" -")
        return (name or "Literature Tutor") + ".md"

    @staticmethod
    def _yaml_string(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    def save(self, request_data: dict[str, Any]) -> dict[str, Any]:
        if self.vault is None or self.error:
            raise ValueError(self.error or "Obsidian 尚未配置")
        paper = request_data.get("paper") if isinstance(request_data.get("paper"), dict) else {}
        context = request_data.get("context") if isinstance(request_data.get("context"), dict) else {}
        title = self._clean(paper.get("title"), 500)
        authors = self._clean(paper.get("authors"), 800)
        year = self._clean(paper.get("year"), 20)
        doi = self._clean(paper.get("doi"), 200)
        question = self._clean(request_data.get("question"), 8_000)
        answer = self._clean(request_data.get("answer"), 40_000)
        selection = self._clean(request_data.get("selection"), 4_000)
        user_note = self._clean(request_data.get("userNote"), 8_000)
        raw_tags = request_data.get("tags") if isinstance(request_data.get("tags"), list) else []
        tags = [re.sub(r"[^\w\-/\u4e00-\u9fff]", "", self._clean(tag, 60)).strip("-/") for tag in raw_tags]
        tags = [tag for tag in tags if tag][:12]
        if not title or not question or not answer:
            raise ValueError("论文标题、问题和回答不能为空")

        context_label = self._clean(context.get("label"), 300) or "整篇论文"
        context_kind = self._clean(context.get("kind"), 80) or "paper"
        digest_source = "\n".join((doi or title, context_label, question, answer))
        block_id = "ipr-" + hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:12]
        note_name = self._filename(title, authors, year)
        note_dir = (self.vault / self.papers_dir).resolve()
        if not note_dir.is_relative_to(self.vault):
            raise ValueError("目标笔记目录越过了 Vault 边界")
        note_path = note_dir / note_name
        relative_path = note_path.relative_to(self.vault).as_posix()
        vault_uri = quote(self.vault.name, safe="")
        file_uri = quote(relative_path.removesuffix(".md"), safe="/")
        uri = f"obsidian://open?vault={vault_uri}&file={file_uri}&block={quote(block_id, safe='')}"

        with self.lock:
            note_dir.mkdir(parents=True, exist_ok=True)
            existing = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
            if f"^{block_id}" in existing:
                return {
                    "ok": True,
                    "duplicate": True,
                    "notePath": relative_path,
                    "blockId": block_id,
                    "uri": uri,
                }
            if not existing:
                citekey_author = note_name.split(" ", 1)[0]
                citekey = re.sub(r"\W+", "", citekey_author + year, flags=re.UNICODE) or block_id
                frontmatter = "\n".join(
                    (
                        "---",
                        "type: paper",
                        f"citekey: {self._yaml_string(citekey)}",
                        f"title: {self._yaml_string(title)}",
                        f"authors: {self._yaml_string(authors)}",
                        f"year: {self._yaml_string(year)}",
                        f"doi: {self._yaml_string(doi)}",
                        "status: reading",
                        "tags:",
                        "  - paper",
                        "  - interactive-reader",
                        "---",
                        "",
                        f"# {title}",
                        "",
                        f"- **Authors:** {authors}",
                        f"- **Year:** {year}",
                        f"- **DOI:** {doi}",
                        "",
                        "## Reader captures",
                        "",
                    )
                )
                existing = frontmatter

            timestamp = datetime.now().astimezone().isoformat(timespec="minutes")
            tag_line = " ".join(f"#{tag}" for tag in tags)
            capture = [
                f"### {context_label}",
                "",
                f"> [!question] 问题",
                *[f"> {line}" for line in question.splitlines()],
                "",
                "**Codex 回答**",
                "",
                answer,
            ]
            if selection:
                capture.extend(("", "**当时选中的原文**", "", f"> {selection.replace(chr(10), chr(10) + '> ')}"))
            if user_note:
                capture.extend(("", "> [!note] 我的笔记", *[f"> {line}" for line in user_note.splitlines()]))
            capture.extend(
                (
                    "",
                    f"- 阅读位置：{context_label} (`{context_kind}`)",
                    f"- 收藏时间：{timestamp}",
                    *( [f"- 标签：{tag_line}"] if tag_line else [] ),
                    "",
                    f"^{block_id}",
                    "",
                )
            )
            new_content = existing.rstrip() + "\n\n" + "\n".join(capture)
            temporary = note_path.with_suffix(".md.tmp")
            temporary.write_text(new_content, encoding="utf-8")
            os.replace(temporary, note_path)

        return {
            "ok": True,
            "duplicate": False,
            "notePath": relative_path,
            "blockId": block_id,
            "uri": uri,
        }


class CodexTutor:
    """Small synchronous client for one local ``codex app-server`` process."""

    def __init__(self, cwd: Path, model: str = "") -> None:
        self.cwd = cwd
        self.model = model
        self.process: subprocess.Popen[bytes] | None = None
        self.messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self.pending: deque[dict[str, Any]] = deque()
        self.stderr_tail: deque[str] = deque(maxlen=20)
        self.lock = threading.Lock()
        self.next_id = 1
        self.thread_id: str | None = None
        self.account_type: str | None = None
        self.plan_type: str | None = None
        self.startup_error: str | None = None

    def _codex_binary(self) -> str:
        configured = os.environ.get("CODEX_BIN", "").strip()
        binary = configured or shutil.which("codex")
        if not binary:
            raise CodexBridgeError("找不到 Codex CLI。请从 ChatGPT 桌面应用打开本项目后再启动阅读器。")
        return binary

    def _stdout_loop(self) -> None:
        assert self.process is not None and self.process.stdout is not None
        for raw in iter(self.process.stdout.readline, b""):
            try:
                value = json.loads(raw.decode("utf-8"))
                if isinstance(value, dict):
                    self.messages.put(value)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

    def _stderr_loop(self) -> None:
        assert self.process is not None and self.process.stderr is not None
        for raw in iter(self.process.stderr.readline, b""):
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                self.stderr_tail.append(line)

    def _send(self, payload: dict[str, Any]) -> None:
        if self.process is None or self.process.poll() is not None or self.process.stdin is None:
            detail = self.stderr_tail[-1] if self.stderr_tail else "Codex 进程没有运行"
            raise CodexBridgeError(detail)
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        try:
            self.process.stdin.write(line.encode("utf-8"))
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            raise CodexBridgeError(f"无法连接本机 Codex：{error}") from error

    def _next_message(self) -> dict[str, Any]:
        if self.pending:
            return self.pending.popleft()
        try:
            return self.messages.get(timeout=RPC_TIMEOUT_SECONDS)
        except queue.Empty as error:
            raise CodexBridgeError("Codex 回答超时，请稍后重试") from error

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        payload: dict[str, Any] = {"method": method, "id": request_id}
        if params is not None:
            payload["params"] = params
        self._send(payload)
        deferred: list[dict[str, Any]] = []
        while True:
            message = self._next_message()
            if message.get("id") == request_id and "method" not in message:
                self.pending.extend(deferred)
                if message.get("error"):
                    error = message["error"]
                    detail = error.get("message", str(error)) if isinstance(error, dict) else str(error)
                    raise CodexBridgeError(detail)
                result = message.get("result", {})
                return result if isinstance(result, dict) else {}
            if "id" in message and "method" in message:
                # This teaching client never allows tools or approvals.
                self._send(
                    {
                        "id": message["id"],
                        "error": {"code": -32601, "message": "The read-only paper tutor does not handle interactive requests."},
                    }
                )
            else:
                deferred.append(message)

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        self.startup_error = None
        binary = self._codex_binary()
        try:
            self.process = subprocess.Popen(
                [binary, "app-server"],
                cwd=str(self.cwd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            raise CodexBridgeError(f"无法启动 Codex App Server：{error}") from error
        threading.Thread(target=self._stdout_loop, name="codex-reader-stdout", daemon=True).start()
        threading.Thread(target=self._stderr_loop, name="codex-reader-stderr", daemon=True).start()
        self._rpc(
            "initialize",
            {
                "clientInfo": {
                    "name": "scientific_literature_tutor",
                    "title": "Literature Tutor",
                    "version": "0.3.0",
                }
            },
        )
        self._send({"method": "initialized", "params": {}})
        account = self._rpc("account/read", {"refreshToken": False}).get("account")
        if not isinstance(account, dict):
            raise CodexBridgeError("Codex 尚未登录。请先在 ChatGPT/Codex 中使用 ChatGPT 账号登录。")
        self.account_type = str(account.get("type", "unknown"))
        self.plan_type = str(account.get("planType")) if account.get("planType") else None
        if self.account_type != "chatgpt":
            raise CodexBridgeError(
                "当前 Codex 不是 ChatGPT 订阅登录。请先运行 `codex login` 并选择 ChatGPT 登录。"
            )
        self._start_thread()

    def _start_thread(self) -> None:
        params: dict[str, Any] = {
            "cwd": str(self.cwd),
            "approvalPolicy": "never",
            "sandbox": "read-only",
            "personality": "friendly",
            "serviceName": "scientific_literature_tutor",
        }
        if self.model:
            params["model"] = self.model
        result = self._rpc("thread/start", params)
        thread = result.get("thread")
        if not isinstance(thread, dict) or not thread.get("id"):
            raise CodexBridgeError("Codex 没有创建教学对话")
        self.thread_id = str(thread["id"])

    def reset(self) -> None:
        with self.lock:
            self.start()
            self._start_thread()

    def status(self) -> dict[str, Any]:
        with self.lock:
            try:
                self.start()
            except CodexBridgeError as error:
                self.startup_error = str(error)
            return {
                "ok": self.startup_error is None,
                "configured": self.startup_error is None and self.account_type == "chatgpt",
                "provider": "codex-subscription",
                "accountType": self.account_type,
                "planType": self.plan_type,
                "model": self.model or "Codex default",
                "error": self.startup_error,
            }

    @staticmethod
    def _agent_text(item: Any) -> str:
        if not isinstance(item, dict) or item.get("type") != "agentMessage":
            return ""
        for key in ("text", "message"):
            if isinstance(item.get(key), str):
                return item[key]
        content = item.get("content")
        if isinstance(content, list):
            return "".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )
        return ""

    def ask(self, request_data: dict[str, Any]) -> str:
        message = str(request_data.get("message", ""))[:8_000].strip()
        if not message:
            raise ValueError("问题不能为空")
        paper = request_data.get("paper") if isinstance(request_data.get("paper"), dict) else {}
        context = request_data.get("context") if isinstance(request_data.get("context"), dict) else {}
        selection = str(request_data.get("selection", ""))[:2_000].strip()
        source_packet = {
            "paper": paper,
            "current_reader_context": context,
            "selected_text": selection or None,
        }
        prompt = (
            TUTOR_INSTRUCTIONS
            + "\n\n下面是由论文阅读器提供的可核对上下文。只把其中明确出现的信息归于本文：\n"
            + json.dumps(source_packet, ensure_ascii=False, separators=(",", ":"))
            + "\n\n用户问题："
            + message
        )
        with self.lock:
            self.start()
            if not self.thread_id:
                self._start_thread()
            result = self._rpc(
                "turn/start",
                {
                    "threadId": self.thread_id,
                    "input": [{"type": "text", "text": prompt}],
                    "approvalPolicy": "never",
                    "sandboxPolicy": {"type": "readOnly"},
                    "personality": "friendly",
                },
            )
            turn = result.get("turn")
            turn_id = str(turn.get("id")) if isinstance(turn, dict) and turn.get("id") else None
            if not turn_id:
                raise CodexBridgeError("Codex 没有开始回答")
            chunks: list[str] = []
            final_text = ""
            failure = ""
            while True:
                event = self._next_message()
                if "id" in event and "method" in event:
                    self._send(
                        {
                            "id": event["id"],
                            "error": {"code": -32601, "message": "Interactive requests are disabled for this tutor."},
                        }
                    )
                    continue
                method = event.get("method")
                params = event.get("params") if isinstance(event.get("params"), dict) else {}
                event_turn_id = params.get("turnId")
                if method == "item/agentMessage/delta" and (not event_turn_id or str(event_turn_id) == turn_id):
                    delta = params.get("delta")
                    if isinstance(delta, str):
                        chunks.append(delta)
                elif method == "item/completed" and (not event_turn_id or str(event_turn_id) == turn_id):
                    candidate = self._agent_text(params.get("item"))
                    if candidate:
                        final_text = candidate
                elif method == "error":
                    error = params.get("error")
                    if isinstance(error, dict):
                        failure = str(error.get("message", "Codex 回答失败"))
                elif method == "turn/completed":
                    completed = params.get("turn") if isinstance(params.get("turn"), dict) else {}
                    if str(completed.get("id", "")) != turn_id:
                        continue
                    status = completed.get("status")
                    if status != "completed":
                        error = completed.get("error")
                        detail = error.get("message") if isinstance(error, dict) else failure
                        raise CodexBridgeError(str(detail or f"Codex 回答状态：{status}"))
                    break
            answer = final_text or "".join(chunks).strip()
            if not answer:
                raise CodexBridgeError("Codex 没有返回可显示的文本")
            return answer

    def close(self) -> None:
        process = self.process
        self.process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()


class ReaderHandler(SimpleHTTPRequestHandler):
    server_version = "LiteratureTutor/3.0"

    def _origin(self) -> str | None:
        origin = self.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            return origin
        if origin and origin.startswith(("http://127.0.0.1:", "http://localhost:")):
            return origin
        return None

    def end_headers(self) -> None:
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json(200, self.server.tutor.status())
            return
        if path == "/api/obsidian/status":
            self._json(200, self.server.obsidian.status())
            return
        super().do_GET()

    def _read_request(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("无效的 Content-Length") from error
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("请求为空或过大")
        request_data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(request_data, dict):
            raise ValueError("请求必须是 JSON 对象")
        return request_data

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/api/chat", "/api/chat/reset", "/api/obsidian/save"}:
            self._json(404, {"error": "未找到接口"})
            return
        try:
            request_data = self._read_request()
            if path == "/api/obsidian/save":
                self._json(200, self.server.obsidian.save(request_data))
                return
            if path == "/api/chat/reset":
                self.server.tutor.reset()
                self._json(200, {"ok": True})
                return
            answer = self.server.tutor.ask(request_data)
            self._json(
                200,
                {
                    "answer": answer,
                    "provider": "codex-subscription",
                    "model": self.server.tutor.model or "Codex default",
                    "planType": self.server.tutor.plan_type,
                },
            )
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            self._json(400, {"error": str(error)})
        except CodexBridgeError as error:
            self._json(502, {"error": str(error)})
        except Exception as error:  # defensive boundary for a local teaching tool
            self._json(500, {"error": f"本地服务错误：{error}"})


class ReaderServer(ThreadingHTTPServer):
    tutor: CodexTutor
    obsidian: ObsidianBridge

    def server_close(self) -> None:
        self.tutor.close()
        super().server_close()


def default_workspace_root() -> Path:
    """Prefer the caller's project so installed-skill scripts stay portable."""
    current = Path.cwd().resolve()
    if (current / "output" / "html").is_dir() or (current / "paper-readers").is_dir():
        return current
    return Path(__file__).resolve().parents[3]


def parse_args() -> argparse.Namespace:
    workspace_root = default_workspace_root()
    parser = argparse.ArgumentParser(description="Serve paper readers with a ChatGPT-subscription Codex tutor")
    parser.add_argument(
        "--root",
        type=Path,
        default=workspace_root / "output" / "html",
        help="directory containing generated reader HTML files",
    )
    parser.add_argument(
        "--reader",
        default="",
        help="optional reader path relative to --root; omit to show the reader directory",
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind host; keep loopback for local use")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--obsidian-config",
        type=Path,
        default=workspace_root / "paper-readers" / "obsidian-config.json",
        help="JSON file containing the local Obsidian vault path and paper-note directory",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"Root directory does not exist: {root}", file=sys.stderr)
        return 2
    workspace_root = default_workspace_root()
    tutor = CodexTutor(workspace_root, os.environ.get("CODEX_TUTOR_MODEL", "").strip())
    status = tutor.status()
    obsidian = ObsidianBridge(args.obsidian_config)

    handler = lambda *values, **kwargs: ReaderHandler(*values, directory=str(root), **kwargs)
    server = ReaderServer((args.host, args.port), handler)
    server.tutor = tutor
    server.obsidian = obsidian
    atexit.register(tutor.close)

    reader_path = quote(Path(args.reader).as_posix().lstrip("/")) if args.reader else ""
    reader_url = f"http://{args.host}:{args.port}/{reader_path}"
    print(f"Paper reader server: {reader_url}")
    if status["configured"]:
        plan = f" ({status['planType']})" if status.get("planType") else ""
        print(f"Codex tutor: ready via ChatGPT subscription{plan}")
    else:
        print(f"Codex tutor: unavailable — {status.get('error')}")
    print(f"Model: {status['model']}")
    obsidian_status = obsidian.status()
    if obsidian_status["configured"]:
        print(f"Obsidian: {obsidian_status['vaultName']}/{obsidian_status['papersDir']}")
    else:
        print(f"Obsidian: unavailable — {obsidian_status.get('error')}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
