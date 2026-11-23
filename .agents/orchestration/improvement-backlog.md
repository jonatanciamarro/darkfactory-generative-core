# Backlog Contínuo de Melhorias — DarkFactory & Corporate Pipeline (`improvement-backlog.md`)

> **Repositório Persistente de Oportunidades de Evolução do DarkFactory e do Framework**  
> *Governança estrita: Descoberta → Recomendação via `[CORP-PIPELINE / IMPROVEMENT DETECTED]` → Salvamento com Aprovação do Usuário → Implementação.*

---

## 1. Protocolo de Governança do Backlog

Este catálogo preserva ideias e melhorias identificadas pelo **Corp-Pipeline Master Orchestrator** para o projeto **DarkFactory**, garantindo que nenhuma oportunidade valiosa de otimização da esteira cinematográfica ou de governança seja perdida ou implementada sem aprovação prévia.

### Estados do Ciclo de Vida:
- `PROPOSED`: Descoberta inicial pela inteligência do orquestrador; aguardando apreciação do usuário.
- `SAVED_NOT_APPROVED`: Usuário aprovou o salvamento para backlog, mas ainda não autorizou a implementação.
- `APPROVED`: Usuário autorizou formalmente o início do desenvolvimento.
- `IN_PROGRESS`: Em desenvolvimento ativo seguindo o Corp-Pipeline (Fase 1 a 5).
- `IMPLEMENTED`: Código implementado e pre-flight aprovado com testes verdes.
- `VERIFIED`: Validado formalmente em produção ou mergeado no branch principal.
- `REJECTED`: Analisado e descartado com justificativa documentada.
- `DEFERRED`: Postergado para milestones futuras.
- `SUPERSEDED`: Substituído por uma proposta ou arquitetura mais moderna.

---

## 2. Tabela de Registro Geral de Melhorias

| ID | Título da Melhoria | Categoria | Complexidade | Status Atual | Data de Descoberta |
|---|---|---|---|---|---|
| `IMP-0001` | Detecção Automática do `.venv` no `stack_detector.py` | `AUTOMATION` | Baixa (S) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0002` | Circuit Breaker e Reconexão com Backoff no `RemoteMCPSSEClient` | `RELIABILITY` | Média (M) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0003` | Script de Hook `SessionStart` com Injeção de Contexto Corp-Pipeline | `AUTOMATION` | Baixa (S) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0004` | Cache de Indexação AST Baseado em Hash SHA-256 de Conteúdo | `EFFICIENCY` | Média (M) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0005` | Exportação de Diagramas Mermaid Dinâmicos a partir da CLI `dag` | `CAPABILITY` | Baixa (S) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0006` | Motor Nativo de Mutation Testing via AST para Validação de Testes AI | `QUALITY` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0007` | Evaluation-Driven Development (EDD) & Scorecard Semântico | `GOVERNANCE` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0008` | Code GraphRAG & Análise de Blast Radius / Impacto de Mudanças | `EFFICIENCY` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0009` | OpenTelemetry Agent Tracing & Span Telemetry (OTel LLMOps) | `OBSERVABILITY` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0010` | Surgical TDD Runner Integrado ao Git Diff & Blast Radius | `EFFICIENCY` | Baixa-Média (S-M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0011` | MCP Enterprise Hub & Tool Multiplexer (.mcp.json pools) | `INTEGRATION` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0012` | AST Auto-Refactor & Self-Healing Fixer (Auto-Remediação) | `AUTOMATION` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0013` | Contratos Fortemente Tipados Pydantic v2 nos Retornos de `ai_engine_suite.py` | `QUALITY` | Média (M) | `PROPOSED` | `2026-11-20` |
| `IMP-0014` | Redução da Complexidade Ciclomática e Modularização de `StoryValidator` | `ARCHITECTURE` | Média (M) | `PROPOSED` | `2026-11-20` |
| `IMP-0015` | Integração do DAG Orchestrator com Checkpoints de Recuperação no `run_pilot_pipeline.py` | `RELIABILITY` | Média (M) | `PROPOSED` | `2026-11-20` |

---

## 3. Especificação Detalhada das Propostas

### 🔹 IMP-0001: Detecção Automática do `.venv` no `stack_detector.py`
- **Categoria**: `AUTOMATION` | `RELIABILITY`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: No Windows, se o desenvolvedor executa `pytest` ou `python` pelo terminal padrão sem o `.venv` ativado no path, o Python global pode não conter as dependências instaladas (`hypothesis`, `pytest-cov`, `pydantic`), causando falhas falsas. O `stack_detector.py` atualmente emite comandos genéricos como `pytest` ao invés de apontar para `.venv\Scripts\pytest` quando o `.venv` existe localmente.
- **Solução Proposta**: Atualizar `stack_detector.py` para inspecionar se a pasta `.venv` existe no root. Em caso afirmativo no Windows, sugerir `.venv\Scripts\<tool>` ou `.venv/bin/<tool>` em sistemas Unix/macOS.
- **Benefícios Esperados**: Execução determinística dos testes e ferramentas de qualidade sem necessidade de ativação manual do virtualenv.
- **Componentes Afetados**: `.agents/skills/corp-pipeline/scripts/stack_detector.py`.
- **Complexidade**: Baixa (10-15 linhas de código).
- **Riscos**: Mínimos.
- **Critérios de Aceite**: `stack_detector.py` retorna caminhos do virtualenv quando detectado; testes unitários cobrem o comportamento.

---

### 🔹 IMP-0002: Circuit Breaker e Reconexão com Backoff no `RemoteMCPSSEClient`
- **Categoria**: `RELIABILITY` | `CAPABILITY`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: O cliente SSE para MCP (`RemoteMCPSSEClient`) trata desconexões imediatas, mas não possui um padrão de circuit breaker integrado com retentativas automáticas e backoff exponencial quando o endpoint remoto fica intermitente.
- **Solução Proposta**: Implementar padrão Circuit Breaker com três estados (`CLOSED`, `OPEN`, `HALF_OPEN`) e política configurável de reconexão no cliente SSE.
- **Benefícios Esperados**: Resiliência contra flutuações de rede corporativa e proteção contra sobrecarga em endpoints MCP degradados.
- **Componentes Afetados**: `src/corporate_engineer/mcp/client.py`, `tests/test_mcp_client.py`.
- **Complexidade**: Média (estimado: 60-80 linhas com PBT).
- **Riscos**: Complexidade de concorrência em streaming.
- **Critérios de Aceite**: Suíte de testes com simulação de timeout, transição de estados do circuit breaker e 100% dos testes verdes.

---

### 🔹 IMP-0009: OpenTelemetry Agent Tracing & Span Telemetry (OTel LLMOps)
- **Categoria**: `OBSERVABILITY` | `QUALITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-007.md`, `ADR-007`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: A execução de DAGs, nós de agentes e ferramentas MCP não gera traces de telemetria estruturados compatíveis com OpenTelemetry.
- **Solução Proposta**: Implementar módulo `src/corporate_engineer/telemetry/` com `AgentTracer` gerando spans padronizados (`trace_id`, `span_id`, latência, contagem de tokens, prompt/completion payload, status de erro) e exportadores locais para JSON e coletores OTel.
- **Benefícios Esperados**: Observabilidade de nível sênior em produção para mitigar o "observability gap" em sistemas multi-agentes.
- **Componentes Afetados**: `src/corporate_engineer/telemetry/`, `src/corporate_engineer/orchestrator/graph.py`, `src/corporate_engineer/mcp/client.py`.
- **Complexidade**: Média (M).
- **Riscos**: Overhead de serialização se não for mantido assíncrono.
- **Critérios de Aceite**: Spans gerados para cada nó do grafo com validação de formato e testes unitários.

---

### 🔹 IMP-0010: Surgical TDD Runner Integrado ao Git Diff & Blast Radius
- **Categoria**: `EFFICIENCY` | `QUALITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-008.md`, `ADR-008`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: O desenvolvedor ou agente precisa rodar `corporate-engineer blast-radius` manualmente e em seguida copiar o comando de teste para validar mudanças no código.
- **Solução Proposta**: Criar o subcomando `corporate-engineer test-surgical` que inspeciona o `git diff` contra a branch base (ex.: `main`), calcula automaticamente o blast radius dos símbolos/arquivos alterados e executa cirurgicamente apenas os testes afetados.
- **Benefícios Esperados**: Redução de até 80% no tempo de ciclo do loop TDD em repositórios grandes.
- **Componentes Afetados**: `src/corporate_engineer/cli.py`, `src/corporate_engineer/rag/impact.py`.
- **Complexidade**: Baixa-Média (S-M).

---

### 🔹 IMP-0011: MCP Enterprise Hub & Tool Multiplexer (.mcp.json pools)
- **Categoria**: `INTEGRATION` | `CAPABILITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-009.md`, `ADR-009`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: Não há suporte para carregar arquivos de configuração como `.mcp.json` e orquestrar múltiplos servidores corporativos simultaneamente (ex.: GitHub, Jira, Postgres, Sentry).
- **Solução Proposta**: Criar `MCPEnterpriseHub` que lê arquivos `.mcp.json`, instancia pools de conexões stdio/SSE com circuit breakers individuais e oferece um namespace unificado de ferramentas.
- **Benefícios Esperados**: Transforma o framework em uma plataforma unificada de consumo MCP enterprise.
- **Componentes Afetados**: `src/corporate_engineer/mcp/hub.py`, `src/corporate_engineer/cli.py`.

---

### 🔹 IMP-0012: AST Auto-Refactor & Self-Healing Fixer (Auto-Remediação)
- **Categoria**: `AUTOMATION` | `QUALITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-010.md`, `ADR-010`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: Quando auditorias detectam violações estruturais, a correção necessita de intervenção manual.
- **Solução Proposta**: Adicionar o comando `corporate-engineer fix --auto` que utiliza `ast.NodeTransformer` para aplicar correções seguras e cirúrgicas sem introduzir regressões.
- **Benefícios Esperados**: Aumento autônomo na pontuação do scorecard semântico sem atrito manual.
- **Componentes Afetados**: `src/corporate_engineer/eval/fixer.py`, `src/corporate_engineer/cli.py`.

---

### 🔹 IMP-0013: Contratos Fortemente Tipados Pydantic v2 nos Retornos de `ai_engine_suite.py`
- **Categoria**: `QUALITY` | `GOVERNANCE`
- **Status**: `PROPOSED`
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: A auditoria EDD detectou múltiplos retornos de dicionários soltos (`dict`) em funções centrais como `check_engine_auth_status` e `test_flow_video`.
- **Solução Proposta**: Criar modelos DTO imutáveis Pydantic v2 para padronizar os contratos entre os motores de vídeo e o dashboard.
- **Benefícios Esperados**: Eliminação de `KeyError`, validação em tempo de compilação/teste e tipagem estrita no Mypy.
- **Componentes Afetados**: `src/video/ai_engine_suite.py`, `src/dashboard/app.py`.
- **Complexidade**: Média (M).

---

### 🔹 IMP-0014: Redução da Complexidade Ciclomática e Modularização de `StoryValidator`
- **Categoria**: `ARCHITECTURE` | `MAINTAINABILITY`
- **Status**: `PROPOSED`
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: O módulo `story_validator.py` acumula auditorias dos 27 livros canônicos em funções extensas com aninhamento excessivo.
- **Solução Proposta**: Decompor as regras em validadores modulares baseados no padrão Chain of Responsibility.
- **Benefícios Esperados**: Alta testabilidade unitária isolada por regra narrativa.
- **Componentes Afetados**: `src/story/story_validator.py`, `tests/test_story_validator.py`.
- **Complexidade**: Média (M).

---

### 🔹 IMP-0015: Integração do DAG Orchestrator com Checkpoints de Recuperação no `run_pilot_pipeline.py`
- **Categoria**: `RELIABILITY` | `AUTOMATION`
- **Status**: `PROPOSED`
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: O pipeline sequencial de 12 etapas do piloto documental reinicia fases anteriores se houver queda de rede em APIs externas.
- **Solução Proposta**: Persistir checkpoints granulares de estado por nó do DAG com reexecução idempotente.
- **Benefícios Esperados**: Zero retrabalho em etapas custosas (render de vídeo e warp vocal).
- **Componentes Afetados**: `run_pilot_pipeline.py`, `src/video/cinematic_pipeline.py`.
- **Complexidade**: Média (M).
