# ADR 0004 — Largada manual pelo botão "Iniciar"

- **Status:** Aceito
- **Data:** 2026-10-28

## Contexto

A câmera está posicionada na linha de chegada e vê apenas a parte final do percurso. Não é possível observar a largada real nem medir o tempo total de prova com precisão. Ainda assim, o usuário quer tempo de chegada e diferença entre os carros.

## Decisão

O instante **t0** é registrado quando o operador clica em **"Iniciar"** na interface. O tempo de chegada de cada carro é `cruzamento - t0`. O ranking usa a ordem real de cruzamento, que independe do clique. A interface deixa explícito que o tempo é uma estimativa da prova.

## Alternativas consideradas

- **Início automático na primeira detecção:** não exige clique, mas o t0 varia conforme o carro entra no quadro e produz tempos ainda menos comparáveis.
- **Luz de largada visível na câmera:** mais preciso e automatizável, porém exige hardware e detecção adicionais. Fica no backlog.
- **Não exibir tempo, apenas ranking:** mais honesto, mas o usuário quer números para a apresentação.

## Consequências

- Positivas: simples, sem hardware extra, e o ranking permanece correto mesmo com erro humano no clique.
- Negativas: o tempo absoluto inclui o atraso humano e não representa a largada real; comparações entre baterias dependem da consistência do operador.
- Mitigações: documentar a limitação na interface e no README; permitir no futuro um modo com luz de largada.
