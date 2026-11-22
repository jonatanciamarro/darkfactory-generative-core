# ADR-07: Adoção do Motor de Motion Design Gemini 4 Argon (Swiss-Telemetry Manifesto)

## Status
Proposto (Gate 1 de Alinhamento e Contratos)

## Contexto
O usuário solicitou que a qualidade dos motion graphics documentais atinja o patamar visual da skill de referência `https://github.com/Emily2040/gemini-4-argon-motion-design`, rejeitando primitivas de desenho 2D programáticas básicas (OpenCV/Pillow).
A referência do Gemini 4 Argon implementa o manifesto estético e cinético **Swiss-Telemetry Kinetic Manifesto** (Josef Müller-Brockmann × GMUNK × Kyle Cooper), estruturado em:
1. Resolução Full HD 1080p determinística em HyperFrames e GSAP 3.14.
2. Tipografia monumental condensada (`Big Shoulders Display` 900 vs 300) combinada com telemetria tabular (`IBM Plex Mono` 400/600) e contraponto editorial humano (`Instrument Serif` Italic).
3. Paleta de alto contraste com alternância entre Dark Polarity (Obsidian `#090A0D`, Elevated Panel `#131722`, Acid Volt `#D4FF00`, Signal Vermilion `#FF4D38`) e Light Polarity (Archival Paper `#F4F1EA`, Carbon Ink `#0B0C10`, Crimson `#B01204`).
4. Stage 3D espacial com perspectiva CSS (`perspective: 1250px`), 5 planos escalonados em Z (`Z=-200px` a `Z=+200px`) controlados por gimbal 3-eixos Euler (`rotationX`, `rotationY`, `rotationZ`).
5. Trajetórias balísticas procedurais com splines Catmull-Rom (`strokeDashoffset`), corredores de dispersão normal (`±2σ`), e mira com trava cinemática de anomalia (`+4.82σ`).
6. Renderização seekable determinística via Playwright Headless Chromium (`window.__timelines["main"].seek(t)`), canalizando frames diretamente para codificação H.264 no FFmpeg sem artefatos ou quedas de frame rate.

## Decisão Técnica
Implementar o módulo canônico `src/video/argon_documentary_motion.py` no DarkFactory integrando:
- Modelos Pydantic v2 estritos para configuração de cenas documentais (`ArgonDocumentaryConfig`).
- Quatro arquétipos visuais de estúdio calibrados para documentários dark investigativos:
  - `RADAR_TELEMETRY`: Alerta de mísseis nucleares, radar soviético, trajetória balística Catmull-Rom, retículo de mira `+4.82σ`.
  - `ZSPACE_BUNKER_PARALLAX`: Câmera 3D orbital navegando em planos de profundidade no bunker Serpukhov-15 com fotos históricas reais.
  - `CLASSIFIED_DOSSIER_INVERSION`: Inversão de polaridade por obturador mecânico para dossiê em papel de arquivo, carimbo "CONFIDENTIAL", relatórios desclassificados.
  - `NETFLIX_OSINT_STAGE`: Estação de investigação estilo Netflix com janelas translúcidas, coordenadas de mapa, satélites Oko e telemetria militar.
- Inclusão de fontes WOFF2 embutidas e GSAP 3.14 local para renderização 100% offline.
- Renderizador de alta performance Playwright + FFmpeg em `src/video/argon_documentary_motion.py`.
- Integração nativa no Step 3.5 do pipeline (`src/generate_motion_assets.py`) com exportação direta para `data/broll/` e `data/final/motion_overlays/`.

## Consequências
- **Positivas**: Eliminação definitiva de gráficos sintéticos de baixa fidelidade; fidelidade idêntica ao showreel de estúdio do Gemini 4 Argon; conformidade total WCAG AA e zero colisões de layout; reprodução determinística frame-a-frame.
- **Riscos & Mitigações**: A renderização via Playwright Chromium requer alguns segundos a mais por take do que OpenCV direto; mitigado com pipeline concorrente de captura e modo rápido de preview/testes.
