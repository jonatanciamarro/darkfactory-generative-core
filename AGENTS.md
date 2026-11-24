# DarkFactory — Autonomous Meta-Orchestrator Protocol (Orquestrador Mestre Corporativo)

@[Contexto do Projeto](PROJECT_CONTEXT.md)

> **DIRETIVA MANDATÓRIA PERMANENTE**: O assistente opera sob o **CORPORATE 5-PHASE PIPELINE (`corp-pipeline`)** como padrão canônico para qualquer solicitação, nova feature, correção de bug ou refatoração. A esteira garante alinhamento de escopo (Gate 1), Shift-Left TDD (testes RED antes do código), implementação cirúrgica (GREEN, máx 3 tentativas), auditoria local pré-flight e entrega corporativa rastreável (Gate 2, feature branch, nunca direto na `main`).

---

## 🏛️ REGRAS DE PRODUÇÃO INEGOCIÁVEIS (ALWAYS ON)

1. **🎙️ Narração SEMPRE pelo CosyVoice (ALWAYS ON)**:
   - A voz oficial do canal dark documental é **estritamente CosyVoice 3** (Instruct 2 / Narrator Lock).
   - O modelo local Kokoro-82M ONNX é restrito unicamente a mock de testes ou contingência extrema de rede.

2. **🌌 Google Flow ALWAYS ON**:
   - Geração de takes visuais generativos Dual-Shot via **Google Flow** (Omni Flash Shot A Drama + Veo 3.1 Shot B Macro).
   - Trilha sonora orquestral contínua Zimmer/Lyria via **Flow Music** masterizada a -14 LUFS.

3. **🎬 Motion Cinemático Investigativo Netflix/BBC via Cinetic (ALWAYS ON)**:
   - Todo módulo de motion graphics, mapas vetoriais, esquemas isométricos CAD e overlays táticos opera obrigatoriamente pelo motor **Cinetic** (HyperFrames/GSAP) com paleta investigativa `inkStage` (#0D0B0A, #DC2626, #F2EFEF) e fotos 4K upscaladas pelo **SeedVR 2.5**.

---

## 🧭 O Ciclo Corporativo de 5 Fases (Padrão Mandatório)

### Fase 1: Alinhamento, Contratos & Escopo (🔴 Gate 1 de Confirmação)
1. **Análise de Requisitos**: Receba a demanda ou ticket JIRA/Linear e mapeie regras de negócio e edge cases.
2. **Definição de Contratos & DTOs**: Especifique os tipos de dados, schemas de validação (Pydantic, interfaces) e um breve ADR (Architecture Decision Record) justificando as decisões técnicas.
3. **Gate 1 Humano**: Apresente a proposta de contratos e **PARE** para obter a confirmação explícita (`proceed` / `sim`) do usuário antes de criar ou modificar qualquer código de produção.

### Fase 2: Shift-Left TDD (Contratos em Código)
1. **Detecção de Stack**: Execute `python .agents/skills/corp-pipeline/scripts/stack_detector.py` para identificar comandos de teste e lint da stack ativa.
2. **Criação de Testes Automatizados**: Escreva os testes unitários e de integração baseados estritamente nos contratos da Fase 1.
3. **Certificação RED**: Execute a suíte e garanta que os testes **falham estritamente pelo motivo esperado** antes de qualquer implementação.

### Fase 3: Implementação Cirúrgica & Auto-Recuperação
1. **Implementação Mínima**: Escreva apenas o código de produção necessário para fazer a suíte passar (GREEN).
2. **Auto-Recuperação Cirúrgica (Teto: 3 Tentativas)**: Se testes falharem, diagnostique o traceback isolado e aplique ajustes pontuais (lógica -> tipagem -> contrato). Se a falha persistir após 3 tentativas, interrompa, exiba o diagnóstico e solicite direcionamento.

### Fase 4: Pre-Flight Gate & Auditoria Local
Antes de prosseguir para entrega, execute e aprove todos os 4 pilares:
1. **Linter & Compilação**: Zero warnings ou erros de sintaxe (`py_compile`, `ruff`, `eslint`).
2. **Tipagem Estrita**: Verificação de tipos (`mypy`, `tsc`).
3. **Secret Scan**: Varredura regex assegurando zero credenciais, tokens de API ou senhas expostas.
4. **Regressão Global**: Suíte completa de testes do repositório 100% verde.

### Fase 5: Entrega Corporativa & Governança Git (🔴 Gate 2 de Confirmação)
1. **Gate 2 Humano**: Apresente o resumo das alterações, diff e evidências da auditoria para validação final.
2. **Governança de Branches (Zero Push na Main)**:
   - **É TERMINANTEMENTE PROIBIDO realizar commits ou push direto na `main` ou `master`**.
   - Crie obrigatoriamente uma branch convencional: `git checkout -b feat/<ticket>-<slug>` ou `fix/<ticket>-<slug>`.
3. **Commits Semânticos**: Commits atômicos no padrão Conventional Commits (`feat:`, `fix:`, `refactor:`).
4. **Push Remoto & Pull Request**: Sincronize a feature branch com a origin (`git push -u origin <branch>`) e gere a descrição completa do Pull Request via template corporativo (`.github/PULL_REQUEST_CORP_PIPELINE.md`).

---

## 🎭 Matriz de Roteamento Especializado DarkFactory

| Tipo de Demanda | Subagente Recomendado | Skill / Regra a Consultar | Ferramentas Críticas |
| :--- | :--- | :--- | :--- |
| **Nova Feature, Bugfix & Engenharia Corporativa** | `tdd-guide` / `architect` | `corp-pipeline`, `tdd-workflow` | `run_command`, `write_file`, `edit_file` |
| **Showrunner, Roteiro & Storyboard Não-Linear** | `nolan-director` | `darkfactory-nolan`, `nolan-dark-history-director` | `read_file`, `write_file` |
| **Pesquisa Histórica & Verificação de Fontes** | `architect` | `api-design`, `verification-loop` | `run_command`, `read_file` |
| **Engenharia Vocal & Mixagem Acústica (-14 LUFS)** | `python-reviewer` | `python-patterns`, `darkfactory-review` | `run_command`, `edit_file` |
| **Fábrica de Vídeo T2V (RunningHub / MiniMax / Wan)** | `e2e-runner` | `darkfactory-pipeline`, `error-handling` | `run_command`, `edit_file` |
| **Cinema Dashboard Web SPA (:8502)** | `architect` | `darkfactory-deploy`, `api-design` | `run_command`, `edit_file` |
| **Qualidade & Testes Automatizados (Pytest)** | `tdd-guide` | `python-testing`, `tdd-workflow` | `run_command` |
| **Segurança & Credenciais (.env)** | `security-reviewer` | `verification-loop` | `read_file` |
| **Orquestração Autônoma & Despacho Multivetorial** | `architect` / `planner` | `orchestrator-v2`, `corp-pipeline` | `run_command`, `write_file` |
| **Frescor Arquitetural & Eliminação de Código Obsoleto** | `codebase-freshness-sentinel` | `codebase-freshness-sentinel`, `verification-loop` | `run_command`, `read_file`, `edit_file` |

---

## 🛠️ Suíte de Qualidade Corporativa (`corporate-engineer`)

O framework `corporate-engineer` está instalado no ambiente virtual (`venv\Scripts\corporate-engineer`). Utilize os subcomandos para garantir máxima qualidade e conformidade:

| Operação de Qualidade | Comando Oficial | Finalidade |
|---|---|---|
| **Auditoria Pre-Flight** | `venv\Scripts\corporate-engineer audit` | Validação estática, linter e scan de segredos |
| **Scorecard Semântico (EDD)** | `venv\Scripts\corporate-engineer eval src` | Avaliação em 5 eixos corporativos (0 a 100) |
| **Auto-Remediação AST (Self-Healing)** | `venv\Scripts\corporate-engineer fix --auto --target src` | Correção cirúrgica de violações semânticas |
| **Análise de Blast Radius** | `venv\Scripts\corporate-engineer blast-radius <alvo>` | Grafo de impacto e testes dependentes |
| **Execução Cirúrgica de Testes** | `venv\Scripts\corporate-engineer test-surgical` | Execução dos testes afetados pelo git diff |
| **PR 1-Clique Pré-Preenchido** | `venv\Scripts\corporate-engineer pr-link` | Gera URL para abertura automática de PR no GitHub |
| **MCP Enterprise Hub** | `venv\Scripts\corporate-engineer mcp hub-list` | Catálogo e pools de servidores MCP corporativos |
| **Gemini LoRA DarkFactory (ADR-020)** | `venv\Scripts\corporate-engineer lora [generate|validate|export]` | Geração sintética, validação AST e exportação Vertex AI SFT para motion & tool calling |
| **Antecipação Proativa (IMP-0025)** | `venv\Scripts\corporate-engineer anticipate <prompt>` | Motor tático de antecipação 2 passos à frente e blast radius |

---

### Transparência Operacional
Ao executar ações no projeto, identifique brevemente a rota corporativa:
`🎯 Orquestrador: [Skill: <nome> | Agente: <nome> | Ferramenta: <nome>]`

