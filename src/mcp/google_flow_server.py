#!/usr/bin/env python3
"""DarkFactory Google Flow Native Model Context Protocol (MCP) Server.

Exposes Google Flow generation, video asset inventory, and clip synchronization
as standard MCP Tools over stdio JSON-RPC 2.0 (MCP Protocol Version 2024-11-05).
Compatible with Claude Desktop, Cursor, Windsurf, Antigravity, and any MCP client.
"""

import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# ADR-01: Windows UTF-8 stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

# Set up logging to stderr (stdout is strictly reserved for JSON-RPC messages!)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [GoogleFlowMCP] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("GoogleFlowMCP")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
BROLL_DIR = DATA_DIR / "broll"
SCRIPTS_DIR = DATA_DIR / "scripts"

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "darkfactory-google-flow"
SERVER_VERSION = "1.0.0"


def get_mcp_tools_definitions() -> List[Dict[str, Any]]:
    """Returns the JSON Schema tool definitions exposed by this MCP server."""
    return [
        {
            "name": "flow_audit_inventory",
            "description": "Audita todos os takes de vídeo já gerados no DarkFactory (em data/broll/ e pastas opcionais), retornando cobertura percentual e tempo de GPU economizado.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "search_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Diretórios adicionais para busca de clipes (ex: pasta Downloads).",
                    },
                    "total_scenes": {
                        "type": "integer",
                        "default": 40,
                        "description": "Total de cenas do documentário (padrão: 40 cenas = 80 takes).",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["text", "json"],
                        "default": "text",
                        "description": "Formato de saída do relatório.",
                    },
                },
            },
        },
        {
            "name": "flow_get_pending_scenes",
            "description": "Retorna a lista exata de IDs de cenas faltantes para Shot A (Omni Flash) e Shot B (Veo 3.1 4K).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "total_scenes": {
                        "type": "integer",
                        "default": 40,
                        "description": "Total de cenas exigidas.",
                    },
                },
            },
        },
        {
            "name": "flow_generate_scene",
            "description": "Dispara a geração automatizada de uma tomada específica no Google Flow (com fallback automático para RunningHub MiniMax H3).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "scene_id": {
                        "type": "integer",
                        "description": "Número da cena (1 a 40).",
                    },
                    "shot_type": {
                        "type": "string",
                        "enum": ["shot_a", "shot_b"],
                        "default": "shot_a",
                        "description": "Tipo de tomada: 'shot_a' (Omni Flash continuidade) ou 'shot_b' (Veo 3.1 4K hero/macro).",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Prompt cinematográfico customizado. Se omitido, utiliza o prompt da fila canônica de Nolan.",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": False,
                        "description": "Se verdadeiro, simula a geração sem abrir navegador.",
                    },
                    "prefer_upscale": {
                        "type": "boolean",
                        "default": True,
                        "description": "Prioriza download em 1080p/4K com upscale.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Diretório de destino do vídeo (padrão: data/broll/).",
                    },
                },
                "required": ["scene_id"],
            },
        },
        {
            "name": "flow_sync_clips",
            "description": "Importa e padroniza clipes soltos baixados externamente (ex: pasta Downloads) para data/broll/ com nomes canônicos (scene_{id}.mp4 / scene_{id}_b.mp4).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_dir": {
                        "type": "string",
                        "description": "Diretório onde estão os clipes avulsos a serem importados.",
                    },
                    "target_dir": {
                        "type": "string",
                        "description": "Diretório de destino (padrão: data/broll/).",
                    },
                    "move_file": {
                        "type": "boolean",
                        "default": False,
                        "description": "Se verdadeiro, move os arquivos em vez de copiar.",
                    },
                },
                "required": ["source_dir"],
            },
        },
        {
            "name": "flow_sync_studio",
            "description": "Navega até o projeto ativo do Google Flow e sincroniza/baixa os takes de vídeo existentes na grade diretamente para data/broll/ em 1080p Aprimorada.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "max_clips": {
                        "type": "integer",
                        "default": 50,
                        "description": "Número máximo de clipes a sincronizar da grade do estúdio.",
                    },
                    "prefer_upscale": {
                        "type": "boolean",
                        "default": True,
                        "description": "Se verdadeiro, prioriza 1080p Aprimorada sobre 720p.",
                    },
                },
            },
        },
    ]


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Executa a ferramenta MCP solicitada e formata a resposta."""
    from src.video.video_inventory import VideoInventoryManager

    mgr = VideoInventoryManager()

    if tool_name == "flow_audit_inventory":
        search_dirs_raw = arguments.get("search_dirs", [])
        search_dirs = [Path(p) for p in search_dirs_raw] if search_dirs_raw else None
        total_scenes = arguments.get("total_scenes", 40)
        fmt = arguments.get("format", "text")

        report = mgr.audit_inventory(search_dirs=search_dirs, total_scenes=total_scenes)
        mgr.export_report(report)

        if fmt == "json":
            return {"content": [{"type": "text", "text": json.dumps(report.to_dict(), indent=2)}]}
        else:
            return {"content": [{"type": "text", "text": mgr.format_console_report(report)}]}

    elif tool_name == "flow_get_pending_scenes":
        total_scenes = arguments.get("total_scenes", 40)
        report = mgr.audit_inventory(total_scenes=total_scenes)
        pending_data = {
            "total_scenes": total_scenes,
            "existing_shot_a_count": report.existing_shot_a_count,
            "existing_shot_b_count": report.existing_shot_b_count,
            "missing_shot_a_ids": report.missing_shot_a_ids,
            "missing_shot_b_ids": report.missing_shot_b_ids,
            "missing_total_takes": report.missing_total_takes,
            "coverage_percentage": round(report.coverage_percentage, 1),
        }
        return {"content": [{"type": "text", "text": json.dumps(pending_data, indent=2)}]}

    elif tool_name == "flow_sync_clips":
        source_dir = Path(arguments["source_dir"])
        target_dir = Path(arguments.get("target_dir", str(BROLL_DIR)))
        move_file = arguments.get("move_file", False)

        ingested = mgr.ingest_clips_from_directory(
            source_dir=source_dir,
            target_broll_dir=target_dir,
            move_file=move_file,
        )

        msg = f"✅ Ingestão concluída: {len(ingested)} clipes padronizados em '{target_dir}'. Arquivos: {[f.name for f in ingested]}"
        return {"content": [{"type": "text", "text": msg}]}

    elif tool_name == "flow_sync_studio":
        from src.google_flow_bot import GoogleFlowBot

        max_clips = arguments.get("max_clips", 50)
        prefer_upscale = arguments.get("prefer_upscale", True)

        bot = GoogleFlowBot()
        summary = bot.execute_playwright_sync(max_clips=max_clips, prefer_upscale=prefer_upscale)

        res = {
            "success": len(summary.downloaded_clips) > 0 or summary.total_tiles_found == 0,
            "project_url": summary.project_url,
            "total_tiles_found": summary.total_tiles_found,
            "downloaded_count": len(summary.downloaded_clips),
            "failed_count": len(summary.failed_clips),
            "success_rate": summary.success_rate,
            "downloaded_clips": summary.downloaded_clips,
        }
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    elif tool_name == "flow_generate_scene":
        from src.google_flow_bot import GoogleFlowBot

        scene_id = int(arguments["scene_id"])
        shot_type = arguments.get("shot_type", "shot_a")
        prompt = arguments.get("prompt", "")
        dry_run = arguments.get("dry_run", False)
        output_dir = Path(arguments.get("output_dir", str(BROLL_DIR)))
        output_dir.mkdir(parents=True, exist_ok=True)

        target_name = f"scene_{scene_id}.mp4" if shot_type == "shot_a" else f"scene_{scene_id}_b.mp4"
        target_file = output_dir / target_name

        bot = GoogleFlowBot(broll_dir=output_dir)

        # Checar se clipe já existe
        existing = bot.find_existing_clip(scene_id, shot_type=shot_type)
        if existing and not dry_run:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "success": True,
                                "scene_id": scene_id,
                                "shot_type": shot_type,
                                "cached": True,
                                "file_path": str(existing),
                                "message": f"Take já existe no disco ({existing.name}). Geração poupada com sucesso!",
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        if dry_run:
            if not target_file.exists():
                target_file.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"DRYRUN_SIMULATED_DATA" * 3000)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "success": True,
                                "scene_id": scene_id,
                                "shot_type": shot_type,
                                "is_dry_run": True,
                                "file_path": str(target_file),
                            },
                            indent=2,
                        ),
                    }
                ]
            }

        # Carregar prompt canônico se não fornecido
        if not prompt:
            queue_name = "google_flow_omni_queue.json" if shot_type == "shot_a" else "google_flow_veo3_queue.json"
            queue_file = SCRIPTS_DIR / queue_name
            if queue_file.exists():
                data = json.loads(queue_file.read_text(encoding="utf-8"))
                for sc in data.get("scenes", []):
                    if sc.get("scene_id") == scene_id:
                        prompt = sc.get("prompt", "")
                        break

        # Executar geração
        model = "gemini-omni-flash-1.2" if shot_type == "shot_a" else "veo-3.1-generate-4k"
        duration = 14.5 if shot_type == "shot_a" else 8.0

        success = bot._execute_playwright_flow_prompt(
            model=model,
            prompt=prompt,
            duration=duration,
            output_file=target_file,
            shot_type=shot_type,
        )

        if not success:
            logger.info("Google Flow falhou. Acionando fallback MiniMax H3...")
            try:
                bot.fallback_to_runninghub_or_procedural(
                    scene_id=scene_id,
                    shot_type=shot_type,
                    target_file=target_file,
                    prompt=prompt,
                    duration=duration,
                    allow_procedural=False,
                )
                success = target_file.exists() and target_file.stat().st_size > 50000
            except Exception as fb_exc:
                logger.error(f"Fallback falhou: {fb_exc}")
                success = False

        res = {
            "success": success,
            "scene_id": scene_id,
            "shot_type": shot_type,
            "file_path": str(target_file),
            "file_size_bytes": target_file.stat().st_size if target_file.exists() else 0,
        }
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    return {
        "isError": True,
        "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
    }


def handle_jsonrpc_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Processa requisições individuais JSON-RPC 2.0 em conformidade com a especificação MCP."""
    if not isinstance(req, dict):
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "Invalid Request: expected JSON object"},
        }

    req_id = req.get("id")
    method = req.get("method")

    # 1. Handshake Initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {
                        "listChanged": False,
                    },
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        }

    # 2. Notificação Inicializada (não retorna resposta)
    elif method == "notifications/initialized":
        logger.info("MCP Client connection initialized successfully.")
        return None

    # 3. Ping
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # 4. Listar Ferramentas
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": get_mcp_tools_definitions(),
            },
        }

    # 5. Executar Ferramenta
    elif method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Invalid params: 'name' is required"},
            }

        try:
            tool_result = execute_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": tool_result,
            }
        except Exception as exc:
            logger.error(f"Erro ao executar tool {tool_name}: {exc}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Tool execution failed: {str(exc)}"}],
                },
            }

    # 6. Método Não Encontrado
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}",
            },
        }


class GoogleFlowMCPServer:
    """Servidor MCP operando sobre stdio I/O."""

    def run_stdio_loop(self) -> None:
        """Loop principal síncrono que processa mensagens JSON-RPC 2.0 linha a linha de stdin."""
        logger.info(f"Starting {SERVER_NAME} v{SERVER_VERSION} on stdio transport...")

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break  # EOF: client disconnected

                line = line.strip()
                if not line:
                    continue

                try:
                    req = json.loads(line)
                except json.JSONDecodeError as jde:
                    err_resp = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {str(jde)}"},
                    }
                    sys.stdout.write(json.dumps(err_resp) + "\n")
                    sys.stdout.flush()
                    continue

                resp = handle_jsonrpc_request(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                    sys.stdout.flush()

            except (KeyboardInterrupt, BrokenPipeError):
                break
            except Exception as e:
                logger.error(f"Unhandled error in stdio loop: {e}")

        logger.info("MCP stdio loop terminated.")


def main():
    server = GoogleFlowMCPServer()
    server.run_stdio_loop()


if __name__ == "__main__":
    main()
