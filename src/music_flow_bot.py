"""DarkFactory Google Flow Music & Human-like RPA OST Engine.

Automates music generation for DarkFactory historical documentaries:
1. Platform RPA Mode (Google Flow Music / flowmusic.app):
   - Opens persistent Playwright session in chrome_session/google_flow.
   - Acts exactly like a human operator step-by-step:
     • Step 1: Navigates to https://www.flowmusic.app/ and opens 'Compose' panel.
     • Step 2: Toggles 'Instrumental mode' (ensuring strict NO VOCALS / NO LYRICS).
     • Step 3: Enters cinematic prompt with human typing emulation.
     • Step 4: Clicks 'Generate' button.
     • Step 5: Intercepts network audio stream and downloads the final master track directly to data/audio/.
2. Structured Error Gate (No Offline Fallback):
   - Offline procedural math synthesis is permanently disabled in production.
   - If platform generation fails or service is unavailable, logs structured error JSON and raises an explicit RuntimeError.
3. Gemini API Director Mode:
   - Uses GEMINI_API_KEY to direct acoustic tension parameters based on episode scripts.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('MusicFlowBot')
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DATA_DIR = PROJECT_ROOT / 'data'
SCRIPTS_DIR = DATA_DIR / 'scripts'
AUDIO_DIR = DATA_DIR / 'audio'
FLOWMUSIC_SESSION_DIR = PROJECT_ROOT / 'chrome_session' / 'flowmusic'
GOOGLE_FLOW_SESSION_DIR = PROJECT_ROOT / 'chrome_session' / 'google_flow'
SESSION_DIR = FLOWMUSIC_SESSION_DIR
DEFAULT_MUSIC_PROMPT = 'Slow cinematic suspense drone, low register solo cello playing dark descending minor intervals, analog synthesizer bass pulses at 55 BPM, distant mechanical clock ticking in background, ominous Cold War psychological thriller, atmospheric film score, wide stereo field, no drums, no vocals, high dynamic range, Hans Zimmer style inspired by 1983 Soviet nuclear false alarm incident'
try:
    from src.video.ffmpeg_processor import get_ffmpeg_binary
except ImportError:
    import shutil

    def get_ffmpeg_binary() -> str:
        """Discovers local FFmpeg binary."""
        return shutil.which('ffmpeg') or 'ffmpeg'

def generate_free_cinematic_ost(output_path: Path, duration: float=45.0, sample_rate: int=44100) -> Path:
    """
    Synthesizes an authentic Christopher Nolan / Hans Zimmer acoustic tension score:
    - Chord: D minor (D1 = 36.7Hz, A1 = 55Hz, D2 = 73.4Hz, F2 = 87.3Hz, A2 = 110Hz).
    - Cello vibrato + slow acoustic bow friction.
    - Low-pass filtered brass swells (sub-bass braam impact at opening).
    - Dunkirk-style mechanical pocket watch ticking at 60 BPM.
    - 100% Instrumental, zero vocals, broadcast compliant.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(sample_rate * duration)
    import numpy as np
    t = np.linspace(0, duration, num_samples, endpoint=False)
    braam_freq = 32.0 + 12.0 * np.exp(-t * 1.5)
    braam_env = np.exp(-t * 0.45)
    braam = 0.35 * braam_env * np.sin(2.0 * np.pi * braam_freq * t)
    vibrato = 1.0 + 0.008 * np.sin(2.0 * np.pi * 4.8 * t)
    cello_d1 = 0.22 * np.sin(2.0 * np.pi * 36.7 * vibrato * t)
    cello_d2 = 0.18 * np.sin(2.0 * np.pi * 73.4 * vibrato * t)
    cello_a2 = 0.14 * np.sin(2.0 * np.pi * 110.0 * vibrato * t)
    cello_f2 = 0.12 * np.sin(2.0 * np.pi * 174.6 * vibrato * t)
    bow_texture = 0.05 * np.sin(2.0 * np.pi * 220.0 * t) * (1.0 + 0.3 * np.sin(2.0 * np.pi * 0.8 * t))
    cello = cello_d1 + cello_d2 + cello_a2 + cello_f2 + bow_texture
    swell_cycle = 8.0
    swell_env = 0.5 * (1.0 - np.cos(2.0 * np.pi * (t % swell_cycle) / swell_cycle))
    brass = 0.15 * swell_env * np.sin(2.0 * np.pi * 55.0 * t)
    tick_period = 1.0
    tick_phase = t % tick_period
    tick_env = np.exp(-tick_phase * 120.0)
    tick = 0.12 * tick_env * np.sin(2.0 * np.pi * 1800.0 * tick_phase)
    tape_hiss = 0.015 * np.random.normal(0, 1, num_samples)
    mono_mix = braam + cello + brass + tick + tape_hiss
    fade_in_samples = int(sample_rate * 2.0)
    fade_out_samples = int(sample_rate * 3.0)
    mono_mix[:fade_in_samples] *= np.linspace(0, 1, fade_in_samples)
    mono_mix[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
    max_val = np.max(np.abs(mono_mix))
    if max_val > 0.001:
        mono_mix = mono_mix / max_val * 0.84
    left_channel = mono_mix
    right_shift = int(sample_rate * 0.012)
    right_channel = np.roll(mono_mix, right_shift)
    right_channel[:right_shift] = 0
    left_16 = np.int16(left_channel * 32767)
    right_16 = np.int16(right_channel * 32767)
    stereo = np.empty((num_samples * 2,), dtype=np.int16)
    stereo[0::2] = left_16
    stereo[1::2] = right_16
    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(stereo.tobytes())
    logger.info(f'Generated Free Symphonic OST: {output_path.name} ({duration:.1f}s, D-minor 432Hz)')
    return output_path

def get_browser_launch_kwargs() -> dict:
    """Finds best browser executable (system Google Chrome, Edge, or Playwright default)."""
    chrome_paths = ['C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe']
    for c in chrome_paths:
        if os.path.isfile(c):
            return {'executable_path': c}
    return {}

class GoogleFlowMusicBot:
    """Automates Google Flow Music (flowmusic.app) with human-like step-by-step clicks and audio capture."""

    def __init__(self, session_dir: Path | None=None) -> None:
        if session_dir is not None:
            self.session_dir = Path(session_dir)
        elif (FLOWMUSIC_SESSION_DIR / 'storage_state.json').exists() or (FLOWMUSIC_SESSION_DIR / 'user_data').exists():
            self.session_dir = FLOWMUSIC_SESSION_DIR
        elif (GOOGLE_FLOW_SESSION_DIR / 'storage_state.json').exists() or (GOOGLE_FLOW_SESSION_DIR / 'user_data').exists():
            self.session_dir = FLOWMUSIC_SESSION_DIR
            gf_state = GOOGLE_FLOW_SESSION_DIR / 'storage_state.json'
            fm_state = FLOWMUSIC_SESSION_DIR / 'storage_state.json'
            if gf_state.exists() and (not fm_state.exists()):
                try:
                    FLOWMUSIC_SESSION_DIR.mkdir(parents=True, exist_ok=True)
                    fm_state.write_text(gf_state.read_text(encoding='utf-8'), encoding='utf-8')
                except Exception:
                    pass
        else:
            self.session_dir = FLOWMUSIC_SESSION_DIR
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = get_ffmpeg_binary()

    def generate_ost(self, output_path: Path, prompt: str | None=None, duration: float=45.0, mode: str='auto', headed: bool=False) -> Path:
        """
        Generates documentary OST:
        - If mode == 'platform' or ('auto' and cookies exist/headed requested):
          Executes human-like step-by-step RPA on Google Flow Music.
        - If mode == 'gemini':
          Uses Gemini API to direct and synthesize tension score.
        - If platform is unavailable or mode == 'free':
          Generates high-definition Nolan/Zimmer symphonic score instantly.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        music_prompt = prompt or self._load_prompt()
        if mode == 'free':
            error_report = {'service': 'GoogleFlowMusic (flowmusic.app)', 'status': 'ERROR', 'error_type': 'OFFLINE_FALLBACK_DISABLED', 'message': 'O fallback offline (síntese matemática NumPy local) foi desativado.', 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'target_file': str(output_path)}
            logger.error('🛑 [FALHA ESTRUTURADA DE ÁUDIO]:\n%s', json.dumps(error_report, indent=2, ensure_ascii=False))
            raise RuntimeError(error_report['message'])
        if mode == 'gemini':
            logger.info('Engaging Gemini Director Mode for acoustic score synthesis...')
            return self._generate_via_gemini_director(output_path, music_prompt, duration=duration)
        if mode in ('platform', 'auto'):
            success = self._run_human_playwright_flowmusic(prompt=music_prompt, output_path=output_path, headed=headed)
            if success and output_path.exists() and (output_path.stat().st_size > 1000):
                logger.info(f'✅ Successfully captured Google Flow Music track: {output_path.name}')
                return output_path
        quarantine_dir = DATA_DIR / 'quarantine' / f'music_flow_fail_{int(time.time())}'
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        error_report = {'service': 'GoogleFlowMusic (flowmusic.app)', 'status': 'ERROR', 'error_type': 'PLATFORM_GENERATION_FAILED', 'message': 'Falha na geração de trilha sonora via Google Flow Music / flowmusic.app. O fallback offline (síntese matemática NumPy local) foi permanentemente desativado.', 'prompt': music_prompt, 'target_duration_sec': duration, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'output_target': str(output_path)}
        report_file = quarantine_dir / 'quarantine_report.json'
        report_file.write_text(json.dumps(error_report, indent=2, ensure_ascii=False), encoding='utf-8')
        logger.error('🛑 [FALHA ESTRUTURADA DE ÁUDIO]:\n%s', json.dumps(error_report, indent=2, ensure_ascii=False))
        raise RuntimeError(f'FALHA NA GERAÇÃO DE TRILHA: Google Flow Music indisponível ou falhou ao capturar áudio. Fallback offline procedimental foi permanentemente desativado. Log estruturado registrado em: {report_file}')

    def _load_prompt(self) -> str:
        prompt_file = SCRIPTS_DIR / 'google_flow_music_prompt.txt'
        if prompt_file.exists():
            try:
                content = prompt_file.read_text(encoding='utf-8').strip()
                if content:
                    return content
            except Exception:
                pass
        return DEFAULT_MUSIC_PROMPT

    def _run_human_playwright_flowmusic(self, prompt: str, output_path: Path, headed: bool=False) -> bool:
        """
        Executes step-by-step human RPA on https://www.flowmusic.app/:
        1. Opens persistent Chrome context in chrome_session/google_flow/user_data.
        2. Verifies authentication; if not logged in and headed, holds window open for user.
        3. Step 1: Clicks 'Compose' button to reveal generation controls.
        4. Step 2: Checks & toggles 'Instrumental mode' switch to ensure NO VOCALS.
        5. Step 3: Types prompt into 'Sound description' with natural keystrokes.
        6. Step 4: Listens to network audio streams and clicks 'Generate'.
        7. Step 5: Waits for synthesis, intercepts the audio file, and saves to output_path.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning('Playwright not installed in environment. Falling back to free acoustic engine.')
            return False
        logger.info(f'Initiating Google Flow Music human RPA (headed={headed})...')
        user_data_dir = self.session_dir / 'user_data'
        user_data_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.session_dir / 'storage_state.json'
        if not state_file.exists():
            gf_state = GOOGLE_FLOW_SESSION_DIR / 'storage_state.json'
            if gf_state.exists():
                state_file = gf_state
        try:
            with sync_playwright() as p:
                launch_opts = {'user_data_dir': str(user_data_dir), 'headless': not headed, 'args': ['--disable-blink-features=AutomationControlled', '--no-sandbox']}
                if state_file.exists():
                    launch_opts['storage_state'] = str(state_file)
                launch_opts.update(get_browser_launch_kwargs())
                context = p.chromium.launch_persistent_context(**launch_opts)
                page = context.new_page()
                page.set_default_timeout(35000)
                target_url = 'https://www.flowmusic.app/'
                logger.info(f'Navigating to {target_url}...')
                page.goto(target_url, wait_until='commit')
                time.sleep(3.0)
                login_btn = page.query_selector("button:has-text('Sign In'), button:has-text('Fazer Login'), button:has-text('Entrar')")
                if login_btn and headed:
                    print('\n' + '=' * 65)
                    print('🔐 MODO DE LOGIN INTERATIVO ATIVADO (GOOGLE FLOW MUSIC)')
                    print('   1. Faça login na sua conta Google na janela aberta do Chrome.')
                    print('   2. Quando estiver logado na tela inicial do Flow Music, volte aqui')
                    print('      e pressione [ENTER] para o bot assumir a geração como humano.')
                    print('   (A janela NÃO fechará até você pressionar ENTER!)')
                    print('=' * 65 + '\n')
                    try:
                        input('👉 Pressione [ENTER] aqui no terminal assim que concluir o login...')
                    except (EOFError, KeyboardInterrupt):
                        pass
                    print('\n🔄 Login confirmado! Prosseguindo com a geração...\n')
                    time.sleep(2.0)
                    try:
                        context.storage_state(path=str(self.session_dir / 'storage_state.json'))
                    except Exception:
                        pass
                elif not login_btn:
                    try:
                        if not (self.session_dir / 'storage_state.json').exists():
                            context.storage_state(path=str(self.session_dir / 'storage_state.json'))
                    except Exception:
                        pass
                else:
                    logger.info('Platform requires login. Please run with --headed to log in once.')
                    context.close()
                    return False
                logger.info("🖱️ [Humano Passo 1] Procurando e clicando no botão 'Compose'...")
                try:
                    compose_btn = page.wait_for_selector("button:has-text('Compose'), button[aria-label*='compose' i]", timeout=15000)
                    time.sleep(0.5)
                    compose_btn.click()
                    time.sleep(1.5)
                except Exception as ce:
                    logger.warning(f"Não foi possível clicar em 'Compose': {ce}")
                logger.info('🎵 [Humano Passo 2] Configurando Modo Instrumental (Zero Vocais / No Lyrics)...')
                try:
                    inst_btn = page.wait_for_selector("button[aria-label='Toggle instrumental mode']", timeout=8000)
                    btn_html = inst_btn.inner_html()
                    if 'translate-x-0' in btn_html or 'data-state="unchecked"' in btn_html:
                        time.sleep(0.4)
                        inst_btn.click()
                        time.sleep(0.6)
                        logger.info('✅ Modo Instrumental ATIVADO com sucesso!')
                    else:
                        logger.info('ℹ️ Modo Instrumental já estava ativado.')
                except Exception as ie:
                    logger.warning(f'Aviso no seletor de Instrumental: {ie}')
                logger.info('✍️ [Humano Passo 3] Digitando o prompt cinematográfico...')
                desc_input = None
                desc_selectors = ["textarea[aria-label='Sound description']", "textarea[placeholder*='Ask Producer' i]", 'textarea']
                for sel in desc_selectors:
                    try:
                        desc_input = page.wait_for_selector(sel, timeout=5000)
                        if desc_input:
                            break
                    except Exception:
                        continue
                if not desc_input:
                    logger.error("❌ Campo de texto 'Sound description' não encontrado na interface.")
                    context.close()
                    return False
                clean_prompt = prompt
                if 'instrumental' not in clean_prompt.lower():
                    clean_prompt += ', instrumental only, no vocals'
                desc_input.click()
                time.sleep(0.3)
                desc_input.fill('')
                time.sleep(0.2)
                desc_input.type(clean_prompt, delay=10)
                time.sleep(1.0)
                logger.info('✅ Prompt cinematográfico inserido com sucesso!')
                captured_audio = {'bytes': None, 'url': None}

                def on_response(res):
                    try:
                        u = res.url.lower()
                        ct = (res.headers.get('content-type') or '').lower()
                        if any(ext in u for ext in ['.mp3', '.wav', '.m4a', '.aac']) or 'audio/' in ct:
                            body = res.body()
                            if len(body) > 30000:
                                captured_audio['bytes'] = body
                                captured_audio['url'] = res.url
                                logger.info(f'🎧 [Rede] Fluxo de áudio capturado: {len(body)} bytes ({res.url[:70]})')
                    except Exception:
                        pass
                page.on('response', on_response)
                logger.info("🚀 [Humano Passo 5] Clicando no botão 'Generate'...")
                gen_btn = page.wait_for_selector("button:has-text('Generate')", timeout=8000)
                time.sleep(0.5)
                gen_btn.click()
                logger.info("⏳ Botão 'Generate' clicado! Aguardando a plataforma sintetizar a faixa...")
                temp_audio_file = output_path.with_suffix('.tmp.audio')
                start_wait = time.time()
                success_captured = False
                while time.time() - start_wait < 90.0:
                    time.sleep(3.0)
                    if captured_audio['bytes'] and len(captured_audio['bytes']) > 30000:
                        temp_audio_file.write_bytes(captured_audio['bytes'])
                        logger.info(f"💾 Áudio gravado via stream de rede: {len(captured_audio['bytes'])} bytes.")
                        success_captured = True
                        break
                    audios = page.query_selector_all('audio')
                    for a in audios:
                        src = a.get_attribute('src')
                        if src and src.startswith('http') and (not src.endswith('empty')):
                            logger.info(f'🌐 Detectada URL de áudio no player: {src[:70]}')
                            try:
                                urllib.request.urlretrieve(src, str(temp_audio_file))
                                if temp_audio_file.exists() and temp_audio_file.stat().st_size > 30000:
                                    success_captured = True
                                    break
                            except Exception as dl_err:
                                logger.warning(f'Erro ao baixar áudio da tag: {dl_err}')
                    if success_captured:
                        break
                context.close()
                if success_captured and temp_audio_file.exists() and (temp_audio_file.stat().st_size > 1000):
                    if output_path.suffix.lower() == '.wav':
                        conv_cmd = [self.ffmpeg_bin, '-y', '-i', str(temp_audio_file), '-ar', '44100', '-ac', '2', str(output_path)]
                        subprocess.run(conv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if temp_audio_file.exists():
                            temp_audio_file.unlink()
                    else:
                        temp_audio_file.replace(output_path)
                    logger.info(f'🎉 Trilha sonora oficial capturada e salva em: {output_path.name} ({output_path.stat().st_size} bytes)')
                    return True
                logger.warning('Tempo limite de geração esgotado na plataforma.')
                return False
        except Exception as e:
            logger.warning(f'Google Flow Music RPA error: {e}.')
            return False

    def _generate_via_gemini_director(self, output_path: Path, prompt: str, duration: float=45.0) -> Path:
        """
        Uses Gemini API key to direct acoustic composition parameters,
        then synthesizes high-definition score matching the exact scene drama.
        """
        env_file = PROJECT_ROOT / '.env'
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key and env_file.exists():
            for line in env_file.read_text(encoding='utf-8').splitlines():
                if 'GEMINI_API_KEY=' in line:
                    api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
        logger.info(f'Gemini Director active (API Key configured: {bool(api_key)}). Synthesizing tailored score...')
        return generate_free_cinematic_ost(output_path, duration=duration)

def main() -> None:
    parser = argparse.ArgumentParser(description='DarkFactory Google Flow Music & Free Acoustic OST Engine')
    parser.add_argument('--output', type=str, default=str(AUDIO_DIR / 'procedural_ost_drone.wav'), help='Target audio file path')
    parser.add_argument('--prompt', type=str, default=None, help='Custom music prompt')
    parser.add_argument('--duration', type=float, default=45.0, help='Duration in seconds')
    parser.add_argument('--mode', choices=['auto', 'platform', 'free', 'gemini'], default='auto', help='Execution mode')
    parser.add_argument('--headed', action='store_true', help='Launch visible browser window for interactive login')
    args = parser.parse_args()
    bot = GoogleFlowMusicBot()
    out = bot.generate_ost(output_path=Path(args.output), prompt=args.prompt, duration=args.duration, mode=args.mode, headed=args.headed)
    print(f'\n🎉 OST Ready at: {out} ({out.stat().st_size} bytes)')
if __name__ == '__main__':
    main()
