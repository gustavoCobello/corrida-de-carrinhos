# ADR 0002 — Detecção por cor em HSV em vez de modelo treinado

- **Status:** Aceito
- **Data:** 2026-10-28

## Contexto

Os carros têm cor sólida predominante e a pista terá fundo neutro. São apenas quatro cores conhecidas e no máximo um carro de cada cor por corrida. O objetivo é simplicidade, execução em CPU e fácil calibração.

## Decisão

Detectar os carros por **segmentação de cor no espaço HSV**, com uma ou mais faixas por cor, limpeza morfológica, filtro de área e escolha do maior contorno. Como cada cor é única na corrida, não é necessário um rastreador multi-objeto complexo: mantém-se um estado por cor.

## Alternativas consideradas

- **YOLO ou modelo customizado:** robusto a variações de luz e fundo, mas exige dependências maiores, treino/anotação e mais CPU/GPU. Complexidade desproporcional ao problema.
- **Detecção por template matching:** frágil a rotação, escala e iluminação.
- **Marcadores ArUco/QR:** muito confiáveis, porém mudam a aparência dos carrinhos e fogem da proposta de reconhecer a cor.

## Consequências

- Positivas: rápido, sem treino, fácil de explicar e calibrar; ideal para fundo neutro.
- Negativas: sensível à iluminação, sombras e reflexos; rosa e vermelho têm matizes próximos e exigem ajuste cuidadoso.
- Mitigações: perfis de calibração por ambiente, ROI restrita à pista, área mínima, histerese e modo de diagnóstico com as máscaras.
- Reavaliar se a detecção se mostrar instável: o HSV pode conviver com um modelo como fallback.
