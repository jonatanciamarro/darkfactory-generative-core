# DarkFactory Production Invariants (Always-On Golden Standards)

> **Mandato Mandatório do Projeto**: Estas três regras são de observância estrita, permanente e obrigatória para qualquer agente autônomo, orquestrador e script de execução no DarkFactory.

---

## 🎙️ Invariante 1: Narração SEMPRE pelo CosyVoice (ALWAYS ON)
- **Motor Canônico Obrigatório**: A narração documental cinematográfica deve ser gerada **exclusivamente via CosyVoice 3** (Instruct 2 via RunningHub ou API direta), utilizando consistência vocal travada (`Narrator Consistency Lock`).
- **Cadência & Direção**: Cadência grave, ritmo cinematográfico (0.95x a 0.98x), pausas dramáticas calculadas e curva broadcast Ableton Live Complex Pro normalizada rigorosamente a **-14.0 LUFS (±0.5)** e **-1.0 dBTP**.
- **Regra de Fallback**: O motor `Kokoro-82M ONNX` ou Edge-TTS é restrito **estritamente a contingência extrema offline / testes rápidos de mock**. O produto final de produção deve ser gerado pelo CosyVoice.

---

## 🌌 Invariante 2: Google Flow ALWAYS ON
- **Motor de Vídeo Generativo Dual-Shot**:
  - Geração de takes visuais primários orientada pela suíte **Google Flow**:
    - **Shot A (Drama / Chiaroscuro)**: Google Flow Omni Flash (1080p cinematic).
    - **Shot B (Macro Tátil / Telemetria)**: Google Flow Veo 3 / 3.1 (4K ultra-detalhado).
- **Trilha Sonora Original (OST)**:
  - Síntese de temas orquestrais autorais via **Flow Music** (Lyria / Hans Zimmer Sound Architecture), gerando stems de pressão acústica com sidechain ducking (-18 dB durante a narração).
- **Sessão Persistente**: A sessão `chrome_session/google_flow` deve ser mantida ativa e validada previamente pelo `auth_gate.py`.

---

## 🎬 Invariante 3: Motion Cinemático Investigativo Netflix/BBC via Cinetic (ALWAYS ON)
- **Motor Canônico de Motion**: O módulo de motion graphics, mapas e esquemas táticos opera **exclusivamente pelo motor Cinetic** (`.agents/skills/cinetic/`, HyperFrames & GSAP).
- **Direção Estética Investigativa**:
  - Padrão documental investigativo de alto padrão (referência **Netflix Documentaries** e **BBC Storyville**).
  - **Paleta Militar Autoral `inkStage`**: `#0D0B0A` (fundo carvão escuro), `#DC2626` (vermelho de alerta tático) e `#F2EFEF` (branco gelo de tipografia técnica).
  - Mapas táticos vetoriais animados (projeções polares, rotas de mísseis, raios de radar).
  - Esquemas isométricos CAD de satélites e componentes mecânicos.
  - Carimbos dinâmicos de documentos secretos com efeito de impacto mecânico e fotos históricas reais upscaladas a 4K via **SeedVR 2.5**.
