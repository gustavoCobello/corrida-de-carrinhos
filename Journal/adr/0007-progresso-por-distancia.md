# ADR 0007 — Progresso visual pela distância normalizada até a linha

- **Status:** Aceito
- **Data:** 2026-10-28

## Contexto

A Fase 4 precisava mostrar o quanto cada carro já se aproximou da chegada sem adicionar sensores, escala física ou um rastreamento de trajetória completo. O sistema já calcula a distância perpendicular do centroide até a linha de chegada em coordenadas normalizadas.

Sem escala em centímetros, não é possível medir a distância total percorrida desde a largada real. Também não há garantia de que o carro faça um caminho reto ou permaneça visível durante toda a prova. Qualquer indicador precisa ser tratado como uma estimativa visual, e não como uma medição oficial.

## Decisão

1. Calcular a distância normalizada até a linha como `|lado| / comprimento_da_linha`.
2. Guardar `start_distance` na primeira detecção da cor depois da largada.
3. Calcular `progresso = 1 - distancia / max(start_distance, 0.02)`, limitado ao intervalo 0–1.
4. Forçar `progresso = 1.0` quando o carro finalizar.
5. Reiniciar o progresso no sorteio, na largada e no reset.
6. Expor o valor arredondado em `CarState.to_dict()` para a interface.
7. Usar o progresso apenas na apresentação; ranking, posição e tempos continuam dependendo exclusivamente do cruzamento da linha.

## Alternativas consideradas

- **Integrar o deslocamento entre frames:** mede caminho percorrido, mas acumula ruído do centroide, sofre com oclusões e não tem ponto final natural sem uma escala de pista.
- **Usar o tempo decorrido dividido por uma duração estimada:** simples, porém não reflete a posição real e fica incorreto quando os carros têm velocidades diferentes.
- **Não exibir progresso:** reduz o escopo, mas perde parte do apelo visual da Fase 4.
- **Rastrear a trajetória completa:** mais preciso, porém exige um modelo de pista e muito mais estado do que o necessário para três carros com cores fixas.

## Consequências

- Positivas: indicador barato, estável e explicável, reaproveitando a geometria da linha; a barra reage à posição real no quadro e zera corretamente em cada corrida.
- Negativas: `start_distance` depende da primeira detecção, então a barra pode começar perto de 0% se o carro já estiver próximo da linha; o valor não representa a distância física percorrida.
- Mitigações: piso de `0.02` para evitar divisão por zero, clamp em 0–1, arredondamento na API e uso exclusivamente visual do dado.
- Reavaliar se o projeto passar a ter escala física ou trajetória calibrada: nesse caso, o progresso pode usar distância real ou integração de caminho.
