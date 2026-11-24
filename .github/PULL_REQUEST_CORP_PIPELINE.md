# fix(pipeline): resolve silent errors, subtitle drift, and dry-run bottlenecks (DF-REMED-01)

> **Ticket/Issue**: `DF-REMED-01`  
> **Type**: Bugfix / Deep Audit & Pipeline Remediation (Swarm Max)  
> **Target Branch**: `main`  
> **Source Branch**: `feat/DF-ORCH-01-corporate-engineer-hooks`

---

## 1. Business Context & Problem Statement
Após a varredura profunda executada pelo Swarm Max, foram detectadas cinco classes de débitos técnicos, falhas silenciosas e descompassos na esteira de produção industrial do DarkFactory:
1. **Descompasso de Executável Python**: O orquestrador mestre (`run_pilot_pipeline.py`) chamava `python` global, causando quebras de import (`corporate_engineer`, `pydantic`) em ambientes Windows com virtualenv ativo.
2. **Saída Silenciosa (Silent Exit Code 0)**: O montador de vídeo (`src/render_pilot_video.py`) falhava na geração mas saía com código 0, mascarando falhas a jusante.
3. **Drift de Legendas SRT**: Em `src/cosyvoice_master.py`, falhas em cenas isoladas usavam `continue`, causando dessincronização 1:1 entre narração e legendas.
4. **Desconexão de Roteiro Manifest**: Módulos prioritários resolviam `pilot_soviet_glitch.json` legado em vez do roteiro canônico de Christopher Nolan (`nolan_soviet_glitch.json`).
5. **Gargalo de Dry-Run & Micro-MP4 Corrompido**: O gerador de motion processava 435 frames de blur via Pillow mesmo com `--dry-run`, e o gerador de broll escrevia bytes de texto crus (`b"dummy_veo3_render_bytes"`) gerando erro downstream no FFmpeg (`moov atom not found`).

---

## 2. Technical Decisions & Trade-offs
1. **Virtualenv Auto-Resolution**:
   - `run_pilot_pipeline.py` agora auto-resolve o binário oficial em `PROJECT_ROOT / "venv" / "Scripts" / "python.exe"`.
2. **Fail-Fast com RuntimeError e Exit Code 1**:
   - Substituição de `continue` silencioso por erro explícito e fail-fast em `src/cosyvoice_master.py` e `src/render_pilot_video.py`.
3. **Priorização Nolan Screenplay Manifest**:
   - `nolan_soviet_glitch.json` é a primeira escolha determinística em todos os resolvedores de caminho.
4. **Micro-MP4 Válido de 1 Segundo**:
   - Substituição de bytes falsos por micro-MP4s válidos codificados via FFmpeg em `src/google_flow_bot.py`.
5. **Otimização de Secret Scanner**:
   - Exclusão de diretórios de modelos pesados (`models/`, `.onnx`, `.bin`) e arquivos > 1MB, reduzindo tempo de pre-commit de >10 minutos para 0.3 segundos.

---

## 3. How to Test & Verification Commands

Para reproduzir todos os testes e a esteira completa:
```powershell
# 1. Executar os 8 testes unitários TDD de conectividade e resiliência
.\venv\Scripts\python.exe -m pytest -v tests/test_pipeline_connectivity.py

# 2. Executar a suíte de regressão global do DarkFactory
.\venv\Scripts\python.exe -m pytest -q

# 3. Executar o ciclo de ponta a ponta (12 passos) em modo dry-run
.\venv\Scripts\python.exe run_pilot_pipeline.py --dry-run

# 4. Executar a auditoria de conformidade corporativa e secrets
.\venv\Scripts\corporate-engineer audit
```

---

## 4. Rollback & Disaster Recovery Plan
Em caso de anomalia ou regressão:
```bash
git checkout feat/DF-ORCH-01-corporate-engineer-hooks
git revert 1112901 -m 1
```

---

## 5. Security & Compliance Checklist
- [x] **Zero Hardcoded Secrets**: Pre-Flight Secret Scanner aprovado (0 findings em < 0.4s).
- [x] **Branch Protection Compliance**: Desenvolvido exclusivamente na branch `feat/DF-ORCH-01-corporate-engineer-hooks` (Zero Push na Main / ADR-06).
- [x] **Scorecard Semântico EDD**: 84.7 / 100.0 (Grade B, Aprovado).
- [x] **Full Regression Integrity**: Suíte global com 465 testes passando (100% GREEN, 0 failures).
- [x] **Pipeline End-to-End**: 12 passos executados com sucesso em `run_pilot_pipeline.py --dry-run`.
