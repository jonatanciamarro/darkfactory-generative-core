"""Shift-Left TDD Suite: Google Flow Multi-Vector Card Capture & Upscale Download.

Verifies:
1. GoogleFlowCaptureResult DTO contract.
2. Upscale resolution priority (1080p / 4K / Upscale before 720p).
3. Multi-vector card locator (DOM recent card selection vs coordinate fallback).
4. Direct video src extraction.
5. End-to-end resilient download capture with retry and upscale preference.
"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch
import pytest

from src.google_flow_bot import (
    GoogleFlowCaptureResult,
    GoogleFlowCardCapturer,
    get_download_resolution_selectors,
    get_download_button_selectors,
    get_card_selectors,
)


class TestGoogleFlowContracts:
    """Verifies DTO contracts and resolution hierarchy."""

    def test_capture_result_dto_success(self, tmp_path):
        dummy_file = tmp_path / "scene_3_shot_a.mp4"
        dummy_file.write_bytes(b"dummy video data exceeding 50kb" * 2000)

        res = GoogleFlowCaptureResult(
            success=True,
            method="dom_card_modal_upscale",
            video_path=dummy_file,
            file_size_bytes=dummy_file.stat().st_size,
            duration_sec=10.5,
            error_message=None,
        )

        assert res.success is True
        assert res.method == "dom_card_modal_upscale"
        assert res.video_path == dummy_file
        assert res.file_size_bytes > 50000
        assert res.error_message is None

    def test_capture_result_dto_failure(self):
        res = GoogleFlowCaptureResult(
            success=False,
            method="timeout",
            video_path=None,
            file_size_bytes=0,
            duration_sec=0.0,
            error_message="Card not located after 3 retries",
        )

        assert res.success is False
        assert res.video_path is None
        assert "not located" in res.error_message

    def test_upscale_resolution_priority(self):
        """MANDATÓRIO: Upscale (1080p/4K) DEVE vir antes de 720p por padrão."""
        selectors = get_download_resolution_selectors(prefer_upscale=True)

        assert isinstance(selectors, list)
        assert len(selectors) >= 3

        # Encontrar os índices das opções
        idx_1080p = next(i for i, s in enumerate(selectors) if "1080p" in s.lower() or "upscale" in s.lower())
        idx_720p = next(i for i, s in enumerate(selectors) if "720p" in s.lower())

        # 1080p/Upscale DEVE ter prioridade absoluta sobre 720p
        assert idx_1080p < idx_720p, f"Upscale (índice {idx_1080p}) deve preceder 720p (índice {idx_720p})"

    def test_download_button_selectors_coverage(self):
        """Verifica se os seletores cobrem português, inglês e menus de contexto."""
        selectors = get_download_button_selectors()

        joined = " ".join(selectors).lower()
        assert "baixar" in joined
        assert "download" in joined
        assert "more_vert" in joined or "mais" in joined or "menu" in joined
        # Novos requisitos: Material symbols e tooltips
        assert "file_download" in joined or "download" in joined
        assert "tooltip" in joined or "aria-label" in joined

    def test_card_selectors_exclude_generic_nav_items(self):
        """MANDATÓRIO: get_card_selectors NÃO pode conter 'div[class*="item"]' que causa colisão de menu."""
        selectors = get_card_selectors()

        assert isinstance(selectors, list)
        assert len(selectors) > 0

        # Garantir ausência de seletores excessivamente genéricos
        for sel in selectors:
            assert 'div[class*="item"]' != sel, f"Seletor perigoso detectado: {sel}"
            assert 'div[class*="menu"]' != sel, f"Seletor perigoso detectado: {sel}"

        # Garantir presença de seletores precisos de vídeo e nós de geração
        joined = " ".join(selectors)
        assert "video" in joined
        assert "generation" in joined or "card" in joined or "node" in joined

    def test_card_selectors_include_angular_web_components(self):
        """MANDATÓRIO: get_card_selectors DEVE incluir Web Components reais do Google Flow Grid."""
        selectors = get_card_selectors()
        joined = " ".join(selectors).lower()
        assert "flow-grid-tile-container" in joined, "Falta 'flow-grid-tile-container' nos seletores de card"
        assert "flow-video-tile" in joined, "Falta 'flow-video-tile' nos seletores de card"
        assert "flow-tile-container" in joined, "Falta 'flow-tile-container' nos seletores de card"
        assert "thumbnail" in joined, "Falta seletor de miniatura 'img.thumbnail' nos seletores de card"

    def test_studio_entrance_selectors_include_project_open(self):
        """MANDATÓRIO: get_studio_entrance_selectors DEVE permitir abrir projetos existentes na landing page."""
        from src.google_flow_bot import GoogleFlowBot
        selectors = GoogleFlowBot.get_studio_entrance_selectors()
        joined = " ".join(selectors).lower()
        assert "abrir projeto" in joined, "Falta seletor para 'Abrir projeto' na lista de entrada do estúdio"
        assert "novo projeto" in joined, "Falta seletor para 'Novo projeto'"


class TestGoogleFlowCardCapturer:
    """Verifies Multi-Vector capture mechanics on mocked Playwright pages."""

    @pytest.fixture
    def capturer(self, tmp_path):
        return GoogleFlowCardCapturer(default_timeout_sec=5.0)

    def test_direct_video_src_extraction(self, capturer, tmp_path):
        """Vetor 2: Se uma tag video tiver src HTTP direto, extrai sem depender de modal."""
        mock_page = MagicMock()
        mock_page.evaluate.return_value = "https://storage.googleapis.com/flow-renders/video_123.mp4"

        out_file = tmp_path / "direct_out.mp4"
        with patch("urllib.request.urlretrieve") as mock_retrieve:
            mock_retrieve.side_effect = lambda url, dest: Path(dest).write_bytes(b"A" * 60000)

            result = capturer.try_direct_video_stream_download(mock_page, out_file)
            assert result.success is True
            assert result.method == "direct_video_src"
            assert result.video_path == out_file

    def test_dom_card_locator_finds_latest_and_clicks(self, capturer):
        """Vetor 1: Localiza o card mais recente no DOM e executa scroll + click."""
        mock_page = MagicMock()
        mock_card = MagicMock()
        mock_page.query_selector_all.return_value = [MagicMock(), mock_card]  # 2 cards

        clicked = capturer.focus_latest_generated_card(mock_page, shot_type="shot_a")
        assert clicked is True
        mock_card.scroll_into_view_if_needed.assert_called()
        mock_card.click.assert_called()

    def test_upscale_selection_over_720p(self, capturer, tmp_path):
        """Verifica que quando 1080p e 720p estão disponíveis, o capturer seleciona 1080p."""
        mock_page = MagicMock()
        mock_dl_btn = MagicMock()
        mock_opt_1080p = MagicMock()
        mock_opt_720p = MagicMock()

        # Mock wait_for_selector: primeiro botão de download, depois opção 1080p
        def mock_wait(selector, timeout=10000):
            if "baixar" in selector.lower() or "download" in selector.lower():
                return mock_dl_btn
            if "1080p" in selector.lower():
                return mock_opt_1080p
            if "720p" in selector.lower():
                return mock_opt_720p
            return None

        mock_page.wait_for_selector.side_effect = mock_wait

        mock_download = MagicMock()
        out_file = tmp_path / "out_1080p.mp4"

        def fake_save_as(path):
            Path(path).write_bytes(b"B" * 75000)

        mock_download.save_as.side_effect = fake_save_as

        mock_dl_info = MagicMock()
        mock_dl_info.value = mock_download
        mock_page.expect_download.return_value.__enter__.return_value = mock_dl_info

        result = capturer.download_from_modal(mock_page, out_file, prefer_upscale=True)
        assert result.success is True
        assert "upscale" in result.method or "1080p" in result.method
        mock_opt_1080p.click.assert_called_once()
        mock_opt_720p.click.assert_not_called()

    def test_full_capture_flow_with_retry_and_upscale(self, capturer, tmp_path):
        """Fluxo completo com auto-recuperação e download em alta resolução."""
        mock_page = MagicMock()
        out_file = tmp_path / "final_upscaled.mp4"

        # Simula: tentativa 1 falha na busca direta, tentativa 2 tem sucesso via modal upscale
        with patch.object(capturer, "try_direct_video_stream_download") as mock_direct:
            mock_direct.return_value = GoogleFlowCaptureResult(success=False, method="direct_video_src")

            with patch.object(capturer, "focus_latest_generated_card", return_value=True):
                with patch.object(capturer, "download_from_modal") as mock_modal:
                    mock_modal.return_value = GoogleFlowCaptureResult(
                        success=True,
                        method="dom_card_modal_1080p_upscale",
                        video_path=out_file,
                        file_size_bytes=80000,
                    )

                    result = capturer.capture_and_download(
                        page=mock_page,
                        output_file=out_file,
                        shot_type="shot_a",
                        prefer_upscale=True,
                    )

                    assert result.success is True
                    assert result.method == "dom_card_modal_1080p_upscale"

    def test_cdk_overlay_interception_fallback_to_dom_evaluate(self, capturer, tmp_path):
        """Verifica que quando o click normal falha por interceptação do Angular CDK, o fallback DOM evaluate é chamado."""
        mock_page = MagicMock()
        mock_dl_btn = MagicMock()
        mock_opt = MagicMock()

        # click normal falha simulando erro do Angular CDK
        mock_opt.click.side_effect = Exception("cdk-overlay-backdrop intercepts pointer events")

        def mock_wait(selector, timeout=10000):
            if "baixar" in selector.lower() or "download" in selector.lower():
                return mock_dl_btn
            if "720p" in selector.lower() or "1080p" in selector.lower():
                return mock_opt
            return None

        mock_page.wait_for_selector.side_effect = mock_wait

        mock_download = MagicMock()
        out_file = tmp_path / "cdk_fallback_video.mp4"
        mock_download.save_as.side_effect = lambda p: Path(p).write_bytes(b"C" * 80000)

        mock_dl_info = MagicMock()
        mock_dl_info.value = mock_download
        mock_page.expect_download.return_value.__enter__.return_value = mock_dl_info

        result = capturer.download_from_modal(mock_page, out_file, prefer_upscale=True)

        assert result.success is True
        mock_opt.evaluate.assert_called_with("el => el.click()")

    def test_find_download_button_unified_bounded_timeout(self, capturer):
        """Verifica que find_download_button usa consulta unificada/ágil e não faz loops sequenciais lentos."""
        mock_page = MagicMock()
        mock_btn = MagicMock()
        mock_page.wait_for_selector.return_value = mock_btn

        btn = capturer.find_download_button(mock_page, timeout_sec=2.0)
        assert btn == mock_btn
        # Deve chamar wait_for_selector com seletores combinados em uma única chamada
        mock_page.wait_for_selector.assert_called_once()
        called_sel = mock_page.wait_for_selector.call_args[0][0]
        assert "download" in called_sel.lower() or "baixar" in called_sel.lower()

    def test_overflow_menu_triggers_resolution_option(self, capturer, tmp_path):
        """Quando o botão direto não aparece, clica no menu de overflow (more_vert) para expor a opção de download."""
        mock_page = MagicMock()
        mock_overflow = MagicMock()
        mock_opt_1080p = MagicMock()

        # Simula wait_for_selector: primeiro retorna botão de overflow, depois a opção 1080p
        def mock_wait(selector, timeout=5000):
            if "more_vert" in selector.lower() or "mais" in selector.lower():
                return mock_overflow
            if "1080p" in selector.lower():
                return mock_opt_1080p
            return None

        mock_page.wait_for_selector.side_effect = mock_wait

        mock_download = MagicMock()
        out_file = tmp_path / "overflow_1080p.mp4"
        mock_download.save_as.side_effect = lambda p: Path(p).write_bytes(b"D" * 85000)

        mock_dl_info = MagicMock()
        mock_dl_info.value = mock_download
        mock_page.expect_download.return_value.__enter__.return_value = mock_dl_info

        result = capturer.download_from_modal(mock_page, out_file, prefer_upscale=True)
        assert result.success is True
        assert "1080p" in result.method or "upscale" in result.method


class TestGoogleFlowStudioSync:
    """Verifies automated synchronization and download of existing clips from active Google Flow studio project."""

    def test_sync_existing_clips_contract_and_execution(self, tmp_path):
        from src.google_flow_bot import GoogleFlowBot, GoogleFlowTileMetadata, GoogleFlowSyncSummary

        bot = GoogleFlowBot(broll_dir=tmp_path)
        mock_page = MagicMock()

        # Simula 2 tiles existentes na grade do estúdio
        tile1 = MagicMock()
        tile1.get_attribute.side_effect = lambda attr: "Soviet duty officer Serpukhov" if attr == "aria-label" else ""
        tile2 = MagicMock()
        tile2.get_attribute.side_effect = lambda attr: "Ballistic missile trajectory" if attr == "aria-label" else ""

        mock_page.query_selector_all.return_value = [tile1, tile2]

        with patch.object(bot.capturer, "download_from_modal") as mock_modal:
            # Simula download bem-sucedido
            def fake_download(page, out_file, prefer_upscale=True):
                Path(out_file).write_bytes(b"DATA" * 20000)
                return GoogleFlowCaptureResult(
                    success=True,
                    method="modal_1080p_upscale",
                    video_path=Path(out_file),
                    file_size_bytes=80000,
                )

            mock_modal.side_effect = fake_download

            summary = bot.sync_existing_project_clips(mock_page, max_clips=2, prefer_upscale=True)

            assert isinstance(summary, GoogleFlowSyncSummary)
            assert summary.total_tiles_found == 2
            assert len(summary.downloaded_clips) == 2
            assert summary.success_rate == 100.0



