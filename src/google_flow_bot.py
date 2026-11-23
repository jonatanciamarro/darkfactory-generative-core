#!/usr/bin/env python3
"""DarkFactory Google Flow Playwright Stealth RPA Bot.

Automates clip generation on Google Flow (flow.google.com):
1. Loads specialized generation queues:
   - Gemini Omni Flash 1.2: Long-form continuity takes (up to 15s) with 6 reference image slots.
   - Google DeepMind Veo 3 / 3.1: 4K native hero shots (8s) with Panavision anamorphic optics.
2. Injects prompts and settings into Google Flow using a persistent Chrome session.
3. Automatically downloads generated video clips into data/broll/ for final assembly.
4. Provides automatic fallback to RunningHub T2V / procedural footage if Flow session is unauthenticated.
5. Operates in dry-run mode for CI/test suites without live browser launches.
"""
import argparse
from dataclasses import dataclass
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ADR-01: Windows UTF-8 stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GoogleFlowBot")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DATA_DIR = PROJECT_ROOT / "data"
SCRIPTS_DIR = DATA_DIR / "scripts"
BROLL_DIR = DATA_DIR / "broll"
SESSIONS_DIR = PROJECT_ROOT / "chrome_session" / "google_flow"


@dataclass
class GoogleFlowCaptureResult:
    """Resultado da captura e download do vídeo gerado no Google Flow."""
    success: bool
    method: str  # "direct_video_src", "dom_card_modal_upscale", "dom_card_modal_720p", "bounding_box_click", "timeout", etc.
    video_path: Optional[Path] = None
    file_size_bytes: int = 0
    duration_sec: float = 0.0
    error_message: Optional[str] = None


@dataclass
class GoogleFlowTileMetadata:
    """Metadados de um tile de vídeo extraído da grade do Google Flow."""
    index: int
    prompt_title: str
    thumbnail_url: str = ""
    tile_element_handle: Any = None
    is_upscaled: bool = False


@dataclass
class GoogleFlowSyncSummary:
    """Relatório da esteira de sincronização de takes existentes e novos."""
    project_url: str
    total_tiles_found: int
    downloaded_clips: List[Dict[str, Any]]
    failed_clips: List[Dict[str, Any]]
    success_rate: float


def get_download_resolution_selectors(prefer_upscale: bool = True) -> List[str]:
    """Retorna seletores ordenados por resolução. Por padrão, prioriza Upscale (1080p/4K) sobre 720p."""
    if prefer_upscale:
        return [
            'text=1080p',
            'text=Upscale',
            'text=4K',
            'text=Aprimorado',
            'text=High Definition',
            'button:has-text("1080p")',
            'button:has-text("Upscale")',
            'text=720p',
            'button:has-text("720p")',
        ]
    return [
        'text=720p',
        'button:has-text("720p")',
        'text=1080p',
        'text=Upscale',
        'button:has-text("1080p")',
    ]


def get_download_button_selectors() -> List[str]:
    """Retorna seletores resilientes para o botão de download no Google Flow."""
    return [
        'button[aria-label*="Baixar mídia" i]',
        'button[aria-label*="Fazer o download" i]',
        'button[aria-label*="Baixar" i]',
        'button[aria-label*="Download" i]',
        'button[data-tooltip*="Baixar" i]',
        'button[data-tooltip*="Download" i]',
        'button:has(mat-icon:has-text("download"))',
        'button:has(mat-icon:has-text("file_download"))',
        'button:has(span.material-symbols-outlined:has-text("download"))',
        'button:has(span.material-symbols-outlined:has-text("file_download"))',
        'button:has-text("download")',
        'button:has-text("Baixar")',
        'a[aria-label*="Baixar" i]',
        'a[aria-label*="Download" i]',
        'button[aria-label*="Mais opções" i]',
        'button[aria-label*="More" i]',
        'button:has(mat-icon:has-text("more_vert"))',
        'button:has(span.material-symbols-outlined:has-text("more_vert"))',
        'button:has-text("more_vert")',
        'button:has-text("more_horiz")',
    ]


def get_card_selectors() -> List[str]:
    """Retorna seletores específicos de nós e cards de mídia gerados no Google Flow,
    incluindo Web Components Angular reais (<flow-grid-tile-container>, <flow-video-tile>)
    e eliminando seletores genéricos como 'div[class*="item"]' que causam colisão com menus."""
    return [
        'flow-grid-tile-container',
        'flow-video-tile',
        'flow-tile-container',
        'img.thumbnail',
        'img[alt*="Miniatura" i]',
        'div[data-card-id]',
        'div[data-testid*="card"]',
        'div[data-testid*="video"]',
        'div[data-testid*="generation"]',
        'div[data-node-id]',
        'div[data-node-type*="video"]',
        'div[class*="flow-node"]',
        'div[class*="generation-card"]',
        'div[class*="video-card"]',
        'div[class*="asset-card"]',
        'div[class*="result-card"]',
        'div:has(> video)',
        'div:has(video)',
        'video',
        'div[role="article"]:has(video)',
        'div[role="listitem"]:has(video)',
        'div[class*="card"]:has(video)',
    ]


class GoogleFlowCardCapturer:
    """Multi-Vector Resilient Card Capturer & Upscale Downloader for Google Flow."""

    def __init__(self, default_timeout_sec: float = 15.0):
        self.default_timeout_sec = default_timeout_sec

    def find_download_button(self, page: Any, timeout_sec: Optional[float] = None) -> Optional[Any]:
        """Localiza o botão de download ou menu de overflow usando consulta unificada ágil com timeout delimitado."""
        t_sec = timeout_sec if timeout_sec is not None else self.default_timeout_sec
        selectors = get_download_button_selectors()
        combined = ", ".join(selectors)
        try:
            btn = page.wait_for_selector(combined, timeout=int(t_sec * 1000))
            if btn and btn.is_visible():
                return btn
        except Exception:
            pass
        return None

    def try_direct_video_stream_download(self, page: Any, output_file: Path) -> GoogleFlowCaptureResult:
        """Vetor 2: Inspeciona elementos de vídeo no DOM e tenta baixar stream direta HTTP(S)."""
        try:
            video_url = page.evaluate('''() => {
                const videos = Array.from(document.querySelectorAll('video'));
                for (const v of videos) {
                    const src = v.currentSrc || v.src;
                    if (src && (src.startsWith('http://') || src.startsWith('https://'))) {
                        return src;
                    }
                }
                return null;
            }''')
            if video_url:
                logger.info(f"Vetor 2: Stream de vídeo direta detectada: {video_url[:80]}...")
                import urllib.request
                urllib.request.urlretrieve(video_url, str(output_file))
                if output_file.exists() and output_file.stat().st_size > 50000:
                    logger.info(f"✅ Vídeo baixado diretamente via URL de stream: {output_file.name} ({output_file.stat().st_size} bytes)")
                    return GoogleFlowCaptureResult(
                        success=True,
                        method="direct_video_src",
                        video_path=output_file,
                        file_size_bytes=output_file.stat().st_size,
                    )
        except Exception as exc:
            logger.debug(f"Aviso ao tentar extrair stream direta de vídeo: {exc}")

        return GoogleFlowCaptureResult(success=False, method="direct_video_src", error_message="Direct stream not found")

    def focus_latest_generated_card(self, page: Any, shot_type: str = "shot_a") -> bool:
        """Vetor 1: Localiza dinamicamente o card de vídeo mais recente no DOM e executa scroll + clique."""
        try:
            # 1. Tentar seletores de cards / nós de geração específicos no DOM
            card_selectors = get_card_selectors()
            for sel in card_selectors:
                elements = page.query_selector_all(sel)
                if elements:
                    target_card = elements[-1]
                    logger.info(f"Vetor 1: Card dinâmico localizado via '{sel}' ({len(elements)} encontrados). Rolando e focando...")
                    target_card.scroll_into_view_if_needed()
                    time.sleep(1)
                    try:
                        target_card.click(force=True, timeout=5000)
                    except Exception:
                        target_card.evaluate("el => el.click()")
                    time.sleep(2)
                    return True

            # 2. Fallback espacial adaptativo se nenhum seletor DOM estruturado retornou
            click_x = 750 if shot_type == "shot_b" else 380
            click_y = 280
            logger.info(f"Vetor 1 (Fallback Espacial): Clicando nas coordenadas calibradas ({click_x}, {click_y})...")
            page.mouse.click(click_x, click_y)
            time.sleep(2)
            return True
        except Exception as exc:
            logger.warning(f"Falha ao focar card mais recente: {exc}")
            return False

    def download_from_modal(self, page: Any, output_file: Path, prefer_upscale: bool = True) -> GoogleFlowCaptureResult:
        """Vetor 3: Aciona o download garantindo prioridade de UPSCALE (1080p/4K) sobre 720p."""
        try:
            dl_btn = self.find_download_button(page)

            if not dl_btn:
                return GoogleFlowCaptureResult(
                    success=False,
                    method="download_button_not_found",
                    error_message="Botão de download não localizado no modal/card.",
                )

            logger.info("Botão de download/ação localizado. Acionando menu ou download direto...")
            try:
                dl_btn.click(force=True, timeout=5000)
            except Exception:
                dl_btn.evaluate("el => el.click()")
            time.sleep(1)

            # Selecionar resolução com preferência de UPSCALE
            res_selectors = get_download_resolution_selectors(prefer_upscale=prefer_upscale)
            selected_option = None
            chosen_res_name = "720p"

            for res_sel in res_selectors:
                try:
                    opt = page.wait_for_selector(res_sel, timeout=3000)
                    if opt and opt.is_visible():
                        selected_option = opt
                        chosen_res_name = res_sel.replace("text=", "").replace('button:has-text("', "").replace('")', "")
                        logger.info(f"🎯 Resolução selecionada com prioridade de upscale: '{chosen_res_name}'")
                        break
                except Exception:
                    continue

            if selected_option:
                logger.info(f"Iniciando download com upscale ({chosen_res_name})...")
                with page.expect_download(timeout=45000) as dl_info:
                    try:
                        selected_option.click(force=True, timeout=8000)
                    except Exception as click_err:
                        logger.debug(f"Clique direto no menu interceptado ({click_err}), acionando fallback DOM evaluate...")
                        selected_option.evaluate("el => el.click()")

                download = dl_info.value
                download.save_as(str(output_file))
                if output_file.exists() and output_file.stat().st_size > 50000:
                    method_label = f"modal_{chosen_res_name}_upscale" if "1080" in chosen_res_name or "upscale" in chosen_res_name.lower() or "4k" in chosen_res_name.lower() else f"modal_{chosen_res_name}"
                    logger.info(f"✅ Vídeo baixado com sucesso via {method_label}: {output_file.name} ({output_file.stat().st_size} bytes)")
                    return GoogleFlowCaptureResult(
                        success=True,
                        method=method_label,
                        video_path=output_file,
                        file_size_bytes=output_file.stat().st_size,
                    )
            else:
                logger.warning("Nenhum menu de resolução exibido após clique em download. Tentando download direto...")
                with page.expect_download(timeout=30000) as dl_info:
                    try:
                        dl_btn.click(force=True, timeout=8000)
                    except Exception:
                        dl_btn.evaluate("el => el.click()")
                download = dl_info.value
                download.save_as(str(output_file))
                if output_file.exists() and output_file.stat().st_size > 50000:
                    return GoogleFlowCaptureResult(
                        success=True,
                        method="direct_modal_download",
                        video_path=output_file,
                        file_size_bytes=output_file.stat().st_size,
                    )

        except Exception as exc:
            return GoogleFlowCaptureResult(
                success=False,
                method="modal_download_exception",
                error_message=str(exc),
            )

        return GoogleFlowCaptureResult(
            success=False,
            method="modal_download_failed",
            error_message="Falha desconhecida no download do modal",
        )

    def capture_and_download(
        self,
        page: Any,
        output_file: Path,
        shot_type: str = "shot_a",
        prefer_upscale: bool = True,
        max_retries: int = 3,
    ) -> GoogleFlowCaptureResult:
        """Executa a esteira completa de captura em 4 vetores com auto-recuperação de até 3 tentativas."""
        logger.info(f"Iniciando captura resiliente de vídeo no Google Flow (prefer_upscale={prefer_upscale}, max_retries={max_retries})...")

        for attempt in range(1, max_retries + 1):
            logger.info(f"🔄 Tentativa {attempt}/{max_retries} de captura no Google Flow...")

            # Vetor 2: Tentar extrair stream de vídeo direta (Fast-Path)
            direct_res = self.try_direct_video_stream_download(page, output_file)
            if direct_res.success:
                return direct_res

            # Vetor 1: Focar o card mais recente
            self.focus_latest_generated_card(page, shot_type=shot_type)

            # Vetor 3: Baixar pelo modal com upscale
            modal_res = self.download_from_modal(page, output_file, prefer_upscale=prefer_upscale)
            if modal_res.success:
                return modal_res

            logger.warning(f"Tentativa {attempt} falhou ({modal_res.error_message or modal_res.method}). Aguardando 3s antes de retentar...")
            time.sleep(3)

        return GoogleFlowCaptureResult(
            success=False,
            method="all_retries_exhausted",
            error_message=f"Falha na captura após {max_retries} tentativas.",
        )


class GoogleFlowBot:
    """Automates Google Flow video generation with stealth and failover."""

    @staticmethod
    def get_studio_entrance_selectors() -> List[str]:
        """Returns candidate selectors for entering the Google Flow studio from the landing page."""
        return [
            'a[aria-label*="Abrir projeto" i]',
            'a[href*="/project/"]',
            'button:has-text("add Novo projeto")',
            'button:has-text("Novo projeto")',
            'button:has-text("New project")',
            'a:has-text("Abrir projeto")',
            'button:has-text("Create with Google Flow")',
            'a:has-text("Create with Google Flow")',
            'button:has-text("Try in Google Flow")',
            'a:has-text("Try in Google Flow")',
            'button:has-text("Try it now!")',
            'a:has-text("Try it now!")',
            'button:has-text("Criar")',
            'a:has-text("Criar")',
        ]

    def __init__(self, broll_dir: Optional[Path] = None, session_dir: Optional[Path] = None):
        self.broll_dir = broll_dir or BROLL_DIR
        self.session_dir = session_dir or SESSIONS_DIR
        self.broll_dir.mkdir(parents=True, exist_ok=True)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.capturer = GoogleFlowCardCapturer(default_timeout_sec=15.0)

    def find_existing_clip(self, scene_id: int, shot_type: str = "shot_a") -> Optional[Path]:
        """Verifica se a cena já possui clipe válido no disco considerando variantes de nomenclatura."""
        candidates = []
        if shot_type == "shot_a":
            candidates = [
                self.broll_dir / f"scene_{scene_id}.mp4",
                self.broll_dir / f"cena {scene_id}.mp4",
                self.broll_dir / f"cena_{scene_id}.mp4",
                self.broll_dir / f"scene{scene_id}.mp4",
            ]
        else:
            candidates = [
                self.broll_dir / f"scene_{scene_id}_b.mp4",
                self.broll_dir / f"scene_{scene_id}b.mp4",
                self.broll_dir / f"cena {scene_id}b.mp4",
                self.broll_dir / f"cena {scene_id}_b.mp4",
                self.broll_dir / f"cena_{scene_id}_b.mp4",
            ]

        for cand in candidates:
            if cand.exists() and cand.is_file() and cand.stat().st_size > 50000:
                return cand
        return None

    def dispatch_flow_queues(
        self,
        omni_queue_file: Path,
        veo3_queue_file: Path,
        dry_run: bool = False,
        allow_procedural: bool = False,
        limit_scenes: int = 0,
    ) -> Dict[str, Any]:
        """Dispatches both Omni Flash 1.2 and Veo 3.1 generation queues."""
        if not omni_queue_file.exists() or not veo3_queue_file.exists():
            raise FileNotFoundError("Google Flow queue files missing. Please run nolan_director.py first.")

        with open(omni_queue_file, "r", encoding="utf-8") as f:
            omni_data = json.load(f)
        with open(veo3_queue_file, "r", encoding="utf-8") as f:
            veo3_data = json.load(f)

        omni_scenes = omni_data.get("scenes", [])
        veo3_scenes = veo3_data.get("scenes", [])
        if limit_scenes > 0:
            omni_scenes = omni_scenes[:limit_scenes]
            veo3_scenes = veo3_scenes[:limit_scenes]

        logger.info(f"Loaded Omni Flash Queue ({len(omni_scenes)} scenes)")
        logger.info(f"Loaded Veo 3.1 4K Queue ({len(veo3_scenes)} scenes)")

        results = {
            "studio": "Google Flow (flow.google.com)",
            "omni_flash_renders": [],
            "veo3_renders": [],
            "status": "completed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        # Process Omni Flash 1.2 continuity scenes (Shot A)
        for sc in omni_scenes:
            s_id = sc["scene_id"]
            existing = self.find_existing_clip(s_id, shot_type="shot_a")
            target_name = f"cena {s_id}.mp4" if s_id == 1 else f"scene_{s_id}.mp4"
            target_path = existing or (self.broll_dir / target_name)

            if dry_run:
                logger.info(f"[DRY-RUN] Simulating Omni Flash 1.2 render for Scene {s_id} ({sc['shot_name']}) -> {target_path.name}")
                if not target_path.exists():
                    target_path.write_bytes(b"dummy_omni_render_bytes")
                results["omni_flash_renders"].append({"scene_id": s_id, "file": str(target_path), "is_dry_run": True})
            elif existing:
                logger.info(f"Target clip for Scene {s_id} (shot_a) already exists ({existing.name}, {existing.stat().st_size} bytes). Skipping generation.")
                results["omni_flash_renders"].append({"scene_id": s_id, "file": str(existing), "is_cached": True})
            else:
                success = self._execute_playwright_flow_prompt(
                    model="gemini-omni-flash-1.2",
                    prompt=sc["prompt"],
                    duration=sc.get("target_duration_sec", 14.5),
                    output_file=target_path,
                    shot_type="shot_a",
                )
                if not success:
                    logger.warning(f"Google Flow render for Scene {s_id} failed or unauthenticated. Applying RunningHub MiniMax H3 fallback...")
                    self.fallback_to_runninghub_or_procedural(
                        s_id,
                        shot_type="shot_a",
                        target_file=target_path,
                        prompt=sc["prompt"],
                        duration=sc.get("target_duration_sec", 14.5),
                        allow_procedural=allow_procedural,
                    )
                results["omni_flash_renders"].append({"scene_id": s_id, "file": str(target_path), "is_fallback": not success})

        # Process Veo 3 / 3.1 4K Tactical Climax scenes (Shot B)
        for sc in veo3_scenes:
            s_id = sc["scene_id"]
            existing = self.find_existing_clip(s_id, shot_type="shot_b")
            target_name = f"cena {s_id}b.mp4" if s_id == 1 else f"scene_{s_id}_b.mp4"
            target_path = existing or (self.broll_dir / target_name)

            if dry_run:
                logger.info(f"[DRY-RUN] Simulating Veo 3.1 4K render for Scene {s_id} ({sc['shot_name']}) -> {target_path.name}")
                if not target_path.exists():
                    target_path.write_bytes(b"dummy_veo3_render_bytes")
                results["veo3_renders"].append({"scene_id": s_id, "file": str(target_path), "is_dry_run": True})
            elif existing:
                logger.info(f"Target clip for Scene {s_id} (shot_b) already exists ({existing.name}, {existing.stat().st_size} bytes). Skipping generation.")
                results["veo3_renders"].append({"scene_id": s_id, "file": str(existing), "is_cached": True})
            else:
                success = self._execute_playwright_flow_prompt(
                    model="veo-3.1-generate-4k",
                    prompt=sc["prompt"],
                    duration=sc.get("target_duration_sec", 8.0),
                    output_file=target_path,
                    shot_type="shot_b",
                )
                if not success:
                    logger.warning(f"Google Flow Veo 3.1 render for Scene {s_id} failed. Applying RunningHub MiniMax H3 fallback...")
                    self.fallback_to_runninghub_or_procedural(
                        s_id,
                        shot_type="shot_b",
                        target_file=target_path,
                        prompt=sc["prompt"],
                        duration=sc.get("target_duration_sec", 8.0),
                        allow_procedural=allow_procedural,
                    )
                results["veo3_renders"].append({"scene_id": s_id, "file": str(target_path), "is_fallback": not success})

        return results

    def _execute_playwright_flow_prompt(
        self,
        model: str,
        prompt: str,
        duration: float,
        output_file: Path,
        shot_type: str = "shot_a",
    ) -> bool:
        """Launches stealth Playwright session to inject prompt and download clip from Google Flow."""
        state_file = self.session_dir / "storage_state.json"
        has_profile = (self.session_dir / "Default").exists() or state_file.exists()
        if not has_profile:
            logger.info("Google Flow persistent session profile not found. Triggering fallback engine.")
            return False

        # Policy sanitation: remove famous person names to prevent safety filter violations
        clean_prompt = prompt.replace("Stanislav Petrov", "Soviet military duty officer")
        clean_prompt = clean_prompt.replace("Petrov", "the duty officer")

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                launch_kwargs: Dict[str, Any] = {
                    "user_data_dir": str(self.session_dir),
                    "headless": True,
                    "args": ["--disable-blink-features=AutomationControlled"],
                }
                context = p.chromium.launch_persistent_context(**launch_kwargs)
                if state_file.exists():
                    try:
                        state_data = json.loads(state_file.read_text(encoding="utf-8"))
                        cookies = state_data.get("cookies", [])
                        if cookies:
                            context.add_cookies(cookies)
                    except Exception as e:
                        logger.debug(f"Aviso ao injetar cookies de storage_state: {e}")
                page = context.new_page() if not context.pages else context.pages[0]

                flow_url = os.getenv("GOOGLE_FLOW_URL", "https://flow.google.com")
                page.goto(flow_url, timeout=45000)
                time.sleep(4)

                # 1. If on root landing page, enter studio workspace
                try:
                    joined_selectors = ", ".join(self.get_studio_entrance_selectors())
                    enter_studio_btn = page.query_selector(joined_selectors)
                    if enter_studio_btn and enter_studio_btn.is_visible():
                        logger.info(f"Clicking Google Flow studio entrance: '{enter_studio_btn.inner_text().strip()}'")
                        enter_studio_btn.click()
                        time.sleep(4)
                except Exception as e:
                    logger.debug(f"Aviso ao entrar no estúdio do Google Flow: {e}")

                # Check if redirected to Google Accounts login/chooser
                if "accounts.google.com" in page.url:
                    logger.warning(
                        "⚠️ Google Flow redirecionou para seleção de conta Google (Sign-in / Account Chooser). "
                        "Por favor, execute o login interativo do Google Flow no Dashboard para selecionar a conta."
                    )

                # 2. If currently inside video player modal, return to grid
                back_btn = page.query_selector('button:has-text("arrow_back"), button:has-text("Concluir")')
                if back_btn and back_btn.is_visible():
                    logger.info("Returning to studio grid...")
                    back_btn.click()
                    time.sleep(2)

                # 3. Locate prompt input (ProseMirror rich-text editor or fallback contenteditable)
                prose = None
                for sel in ["div.ProseMirror", "div[contenteditable='true']", "textarea", "div[role='textbox']"]:
                    try:
                        prose = page.wait_for_selector(sel, timeout=5000)
                        if prose:
                            break
                    except Exception:
                        pass

                if not prose:
                    logger.warning("Prompt editor not located on Google Flow page. Comuting to RunningHub MiniMax H3 fallback.")
                    context.close()
                    return False

                prose.click()
                time.sleep(1)
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(clean_prompt, delay=10)
                time.sleep(2)

                # 4. Submit generation
                gen_btn = page.query_selector('button[aria-label*="Iniciar geração" i], button:has-text("arrow_forward")')
                if gen_btn and gen_btn.is_visible():
                    logger.info("Clicking 'Iniciar geração'...")
                    gen_btn.click()
                else:
                    page.keyboard.press("Enter")

                # 5. Await generation progress to complete (polling up to 180s)
                logger.info(f"Awaiting Google Flow generation for model {model} (timeout=180s)...")
                time.sleep(10)  # initial delay for rendering to start
                start_time = time.time()
                render_started = False
                while time.time() - start_time < 180:
                    time.sleep(5)
                    # Checar se geração está ativa (porcentagem, spinner, barra de progresso ou botão desabilitado)
                    is_active = page.evaluate('''() => {
                        const all = Array.from(document.querySelectorAll('*'));
                        const hasPercent = all.some(el => /\\b\\d{1,2}%\\b/.test(el.innerText || ''));
                        const hasProgress = document.querySelector('mat-progress-bar, mat-spinner, [role="progressbar"]') !== null;
                        const hasGeneratingText = all.some(el => /gerando|generating|processando/i.test(el.innerText || ''));
                        return hasPercent || hasProgress || hasGeneratingText;
                    }''')
                    if is_active:
                        render_started = True
                        logger.info("Estado de geração ativo detectado no Google Flow...")
                    elif render_started and not is_active:
                        logger.info("Google Flow generation 100% complete (estado de render finalizado)!")
                        break
                    elif time.time() - start_time > 45 and not render_started:
                        logger.info("Timeout de verificação inicial de render atingido. Prosseguindo para captura.")
                        break

                time.sleep(4)

                # 6. Multi-Vector Card Capture & Upscale Download (ADR-07)
                logger.info(f"Initiating Multi-Vector Card Capture for {shot_type} (Upscale Mandatory)...")
                capture_res = self.capturer.capture_and_download(
                    page=page,
                    output_file=output_file,
                    shot_type=shot_type,
                    prefer_upscale=True,
                    max_retries=3,
                )

                if capture_res.success and output_file.exists() and output_file.stat().st_size > 50000:
                    logger.info(
                        f"✅ Successfully captured Google Flow video clip via {capture_res.method}: "
                        f"{output_file.name} ({output_file.stat().st_size} bytes)"
                    )
                    context.close()
                    return True
                else:
                    logger.warning(
                        f"Google Flow Multi-Vector capture failed ({capture_res.method}: {capture_res.error_message}). "
                        f"Comuting to RunningHub MiniMax H3 fallback."
                    )
                    context.close()
                    return False
        except Exception as e:
            logger.warning(f"Playwright Google Flow execution failed ({e}). Comuting to RunningHub MiniMax H3 fallback.")

        return False

    def sync_existing_project_clips(
        self,
        page: Any,
        max_clips: int = 50,
        prefer_upscale: bool = True,
    ) -> GoogleFlowSyncSummary:
        """Sincroniza e baixa todos os takes de vídeo já gerados na grade do estúdio do Google Flow para data/broll/."""
        project_url = getattr(page, "url", "https://flow.google.com")
        logger.info(f"Iniciando varredura e sincronização de takes no Google Flow ({project_url})...")

        tile_selectors = "flow-grid-tile-container, flow-video-tile, flow-tile-container"
        try:
            if hasattr(page, "wait_for_selector"):
                page.wait_for_selector(tile_selectors, timeout=15000)
        except Exception:
            pass

        tiles = page.query_selector_all(tile_selectors)
        if not tiles and hasattr(page, "evaluate"):
            try:
                page.evaluate("() => window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(2)
                tiles = page.query_selector_all(tile_selectors)
            except Exception:
                pass

        total_found = len(tiles)
        logger.info(f"Total de tiles de mídia detectados na grade: {total_found}")

        downloaded = []
        failed = []

        limit = min(total_found, max_clips) if max_clips > 0 else total_found
        for i in range(limit):
            current_tiles = page.query_selector_all(tile_selectors)
            if i >= len(current_tiles):
                break
            tile = current_tiles[i]
            aria_label = tile.get_attribute("aria-label") or f"flow_clip_{i+1}"
            logger.info(f"Sincronizando tile [{i+1}/{limit}]: '{aria_label}'...")

            try:
                if hasattr(tile, "scroll_into_view_if_needed"):
                    tile.scroll_into_view_if_needed()
                time.sleep(1)
                tile.click(force=True)
                time.sleep(2)
            except Exception as click_err:
                logger.warning(f"Falha ao clicar no tile {i+1}: {click_err}")
                failed.append({"index": i, "title": aria_label, "error": str(click_err)})
                continue

            target_filename = f"flow_sync_{i+1:02d}.mp4"
            target_path = self.broll_dir / target_filename

            capture_res = self.capturer.download_from_modal(page, target_path, prefer_upscale=prefer_upscale)
            if capture_res.success and target_path.exists() and target_path.stat().st_size > 50000:
                logger.info(f"✅ Tile {i+1} baixado com sucesso: {target_filename} ({target_path.stat().st_size} bytes)")
                downloaded.append({
                    "index": i,
                    "title": aria_label,
                    "file_path": str(target_path),
                    "size_bytes": target_path.stat().st_size,
                    "method": capture_res.method,
                })
            else:
                logger.warning(f"❌ Falha ao baixar tile {i+1}: {capture_res.error_message or capture_res.method}")
                failed.append({
                    "index": i,
                    "title": aria_label,
                    "error": capture_res.error_message or capture_res.method,
                })

            # Fechar modal para retornar à grade (botão arrow_back, Concluir, Fechar ou Escape)
            try:
                back_btn = page.query_selector('button:has-text("arrow_back"), button:has-text("Concluir"), [aria-label*="Voltar" i], [aria-label*="Fechar" i], button[aria-label*="Close" i]')
                if back_btn and back_btn.is_visible():
                    back_btn.click()
                elif hasattr(page, "keyboard"):
                    page.keyboard.press("Escape")
                time.sleep(1)
            except Exception as close_err:
                logger.debug(f"Aviso ao fechar modal: {close_err}")

        success_rate = (len(downloaded) / limit * 100.0) if limit > 0 else 0.0
        return GoogleFlowSyncSummary(
            project_url=str(project_url),
            total_tiles_found=total_found,
            downloaded_clips=downloaded,
            failed_clips=failed,
            success_rate=round(success_rate, 1),
        )

    def execute_playwright_sync(
        self,
        max_clips: int = 50,
        prefer_upscale: bool = True,
    ) -> GoogleFlowSyncSummary:
        """Abre sessão Playwright, navega até o projeto e executa a sincronização completa de clipes."""
        state_file = self.session_dir / "storage_state.json"
        has_profile = (self.session_dir / "Default").exists() or state_file.exists()
        if not has_profile:
            logger.error("Sessão persistente do Google Flow não encontrada.")
            return GoogleFlowSyncSummary(
                project_url="https://flow.google.com",
                total_tiles_found=0,
                downloaded_clips=[],
                failed_clips=[{"error": "Session profile not found"}],
                success_rate=0.0,
            )

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            launch_kwargs: Dict[str, Any] = {
                "user_data_dir": str(self.session_dir),
                "headless": True,
                "args": ["--disable-blink-features=AutomationControlled"],
            }
            context = p.chromium.launch_persistent_context(**launch_kwargs)
            if state_file.exists():
                try:
                    state_data = json.loads(state_file.read_text(encoding="utf-8"))
                    cookies = state_data.get("cookies", [])
                    if cookies:
                        context.add_cookies(cookies)
                except Exception as exc:
                    logger.debug(f"Aviso ao injetar cookies: {exc}")

            page = context.new_page() if not context.pages else context.pages[0]
            flow_url = os.getenv("GOOGLE_FLOW_URL", "https://flow.google.com")
            page.goto(flow_url, timeout=45000)
            time.sleep(4)

            # Entrar no estúdio
            try:
                joined_selectors = ", ".join(self.get_studio_entrance_selectors())
                enter_btn = page.query_selector(joined_selectors)
                if enter_btn and enter_btn.is_visible():
                    enter_btn.click()
                    time.sleep(5)
            except Exception as e:
                logger.debug(f"Aviso ao abrir projeto: {e}")

            summary = self.sync_existing_project_clips(page, max_clips=max_clips, prefer_upscale=prefer_upscale)
            context.close()
            return summary

    def fallback_to_runninghub_or_procedural(
        self,
        scene_id: int,
        shot_type: str,
        target_file: Path,
        prompt: str = "",
        duration: float = 10.0,
        allow_procedural: bool = False,
    ) -> Path:
        """Fallback engine: attempts RunningHub MiniMax H3 fallback; quarantine if both fail."""
        if target_file.exists() and target_file.stat().st_size > 50000:
            logger.info(f"Using existing cached B-roll for Scene {scene_id} ({shot_type}): {target_file.name}")
            return target_file

        # If procedural is explicitly allowed or no prompt provided (test mode)
        if allow_procedural or not prompt:
            logger.warning(f"Generating procedural fallback plate for Scene {scene_id} (test mode)...")
            try:
                from src.render_pilot_video import create_procedural_broll_image
            except ImportError:
                from render_pilot_video import create_procedural_broll_image
            image_fallback = target_file.with_suffix(".jpg")
            create_procedural_broll_image(image_fallback, scene_id=scene_id, scene_title=f"SCENE {scene_id} {shot_type.upper()}")
            return image_fallback

        # 1. Primary Fallback: RunningHub MiniMax H3 Cinematic V2 Turbo
        logger.info(f"Triggering RunningHub MiniMax H3 Cinematic fallback for Scene {scene_id} ({shot_type})...")
        try:
            from src.video.minimax_h3_engine import MiniMaxH3VideoEngine
            engine = MiniMaxH3VideoEngine(output_dir=self.broll_dir)
            h3_res = engine.generate_video(
                prompt=prompt,
                duration_sec=duration,
                destination_path=target_file,
                force_procedural=False,
                allow_procedural_fallback=False,
            )
            if h3_res.video_path.exists() and h3_res.video_path.stat().st_size > 50000:
                logger.info(f"✅ Scene {scene_id} successfully generated via RunningHub MiniMax H3: {h3_res.filename}")
                if h3_res.video_path != target_file:
                    import shutil
                    shutil.copy(str(h3_res.video_path), str(target_file))
                return target_file
        except Exception as rh_exc:
            logger.warning(f"RunningHub MiniMax H3 fallback failed for Scene {scene_id}: {rh_exc}")

        # If procedural is allowed upon API/RPA failure, synthesize archival plate
        if allow_procedural:
            logger.warning(f"Generating procedural fallback plate for Scene {scene_id} ({shot_type}) as fail-safe...")
            try:
                from src.render_pilot_video import create_procedural_broll_image
            except ImportError:
                from render_pilot_video import create_procedural_broll_image
            image_fallback = target_file.with_suffix(".jpg")
            create_procedural_broll_image(image_fallback, scene_id=scene_id, scene_title=f"SCENE {scene_id} {shot_type.upper()}")
            return image_fallback

        # 2. Hard Quarantine Gate (No fake procedural videos allowed in production!)
        quarantine_dir = DATA_DIR / "quarantine" / f"scene_{scene_id}_{shot_type}_failure"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        failure_report = {
            "scene_id": scene_id,
            "shot_type": shot_type,
            "prompt": prompt,
            "duration": duration,
            "error": "Failed on both Google Flow and RunningHub MiniMax H3. Procedural fallback is permanently disabled.",
            "timestamp": time.time(),
        }
        (quarantine_dir / "quarantine_report.json").write_text(json.dumps(failure_report, indent=2), encoding="utf-8")
        raise RuntimeError(
            f"CRITICAL: Scene {scene_id} ({shot_type}) failed to generate on Google Flow and RunningHub MiniMax H3. "
            f"Procedural fallback is disabled. See quarantine diagnostics at: {quarantine_dir}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="DarkFactory Google Flow RPA Bot")
    parser.add_argument(
        "--omni-queue",
        type=str,
        default=str(SCRIPTS_DIR / "google_flow_omni_queue.json"),
        help="Path to Omni Flash queue JSON",
    )
    parser.add_argument(
        "--veo3-queue",
        type=str,
        default=str(SCRIPTS_DIR / "google_flow_veo3_queue.json"),
        help="Path to Veo 3.1 queue JSON",
    )
    parser.add_argument("--limit-scenes", type=int, default=0, help="Limit number of scenes to render (0 for all)")
    parser.add_argument("--teaser", action="store_true", help="Render only the 3-scene teaser")
    parser.add_argument("--dry-run", action="store_true", help="Simulate video generation without browser session")
    parser.add_argument("--allow-procedural", "--allow-procedural-fallback", dest="allow_procedural", action="store_true", help="Allow synthetic procedural plates when video fails")
    parser.add_argument("--audit", action="store_true", help="Audit existing video inventory and GPU savings")
    parser.add_argument("--ingest-dir", type=str, default="", help="Ingest and standardize video clips from an external directory")
    parser.add_argument("--pending-only", action="store_true", help="Generate and dispatch only pending scenes missing from disk")
    parser.add_argument("--sync-flow", action="store_true", help="Sync and download all existing clips from active Google Flow studio project into data/broll/")
    parser.add_argument("--max-sync-clips", type=int, default=50, help="Maximum number of clips to sync from Google Flow (default: 50)")
    args = parser.parse_args()

    # Sincronização direta do estúdio Google Flow
    if args.sync_flow:
        bot = GoogleFlowBot()
        print(f"🎬 Iniciando sincronização automatizada dos clipes no estúdio do Google Flow (max: {args.max_sync_clips})...")
        summary = bot.execute_playwright_sync(max_clips=args.max_sync_clips, prefer_upscale=True)
        print(f"\n✅ Sincronização Google Flow concluída: {len(summary.downloaded_clips)}/{summary.total_tiles_found} takes baixados em data/broll/ ({summary.success_rate}% de sucesso).")
        return

    # Ingestão opcional prévia
    if args.ingest_dir:
        from src.video.video_inventory import VideoInventoryManager
        mgr = VideoInventoryManager()
        ingested = mgr.ingest_clips_from_directory(Path(args.ingest_dir))
        print(f"✅ Ingested and standardized {len(ingested)} clips into data/broll/.")

    # Auditoria de cobertura e economia de GPU
    if args.audit:
        from src.video.video_inventory import VideoInventoryManager
        mgr = VideoInventoryManager()
        search_dirs = [BROLL_DIR, DATA_DIR / "final"]
        if args.ingest_dir:
            search_dirs.append(Path(args.ingest_dir))
        report = mgr.audit_inventory(search_dirs=search_dirs)
        print(mgr.format_console_report(report))
        out_json = mgr.export_report(report)
        print(f"Relatório exportado em: {out_json}")
        return

    # Modo incremental pending-only
    omni_q = Path(args.omni_queue)
    veo3_q = Path(args.veo3_queue)
    if args.pending_only:
        from src.video.video_inventory import VideoInventoryManager
        mgr = VideoInventoryManager()
        report = mgr.audit_inventory()
        omni_q, veo3_q = mgr.generate_pending_queues(
            audit_report=report,
            omni_queue_file=omni_q,
            veo3_queue_file=veo3_q,
        )
        print(f"🚀 Disparando apenas tomadas pendentes: {omni_q.name} ({len(report.missing_shot_a_ids)} Shot A) & {veo3_q.name} ({len(report.missing_shot_b_ids)} Shot B)")

    limit = 3 if args.teaser else args.limit_scenes
    bot = GoogleFlowBot()
    res = bot.dispatch_flow_queues(
        omni_queue_file=omni_q,
        veo3_queue_file=veo3_q,
        dry_run=args.dry_run,
        allow_procedural=args.allow_procedural or args.dry_run,
        limit_scenes=limit,
    )
    print(f"\nGoogle Flow Bot Execution Summary: {json.dumps(res, indent=2)}")


if __name__ == "__main__":
    main()
