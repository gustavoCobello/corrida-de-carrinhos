# ADR 0006 — Chegada por troca de lado com confirmação em frames

- **Status:** Aceito
- **Data:** 2026-10-28

## Contexto

A Fase 3 precisa transformar detecções de cor em chegadas confiáveis. O sistema não tem escala física nem posição 3D: a única informação disponível é o centroide do maior blob de cada cor, quadro a quadro, já recortado pela ROI.

A linha de chegada pode ser horizontal ou diagonal e é calibrada com dois pontos normalizados. O carro pode sumir por oclusão, o centroide pode oscilar e o vídeo pode pular posições quando um objeto entra ou sai rapidamente do quadro. Uma chegada falsa estraga o ranking e é difícil de corrigir depois.

## Decisão

1. Representar a linha como segmento entre `p1` e `p2` e calcular o lado de cada centroide pelo produto vetorial.
2. Só considerar cruzamento quando o lado muda entre duas detecções consecutivas da mesma cor.
3. Confirmar o cruzamento com a interseção real entre o movimento e o segmento, exigindo que o ponto esteja dentro da linha com uma pequena margem nas pontas.
4. Exigir `confirm_frames` frames consecutivos do novo lado para registrar a chegada. O instante gravado é o do primeiro frame que cruzou, não o da confirmação.
5. Ignorar saltos maiores que `0.35` em coordenadas normalizadas, tratando-os como teleporte ou reentrada no quadro; nesse caso, apenas reiniciar a referência lateral.
6. Registrar no máximo uma chegada por cor e encerrar automaticamente a corrida quando todas as cores da formação chegarem. O encerramento manual marca as restantes como `missed`.
7. Manter o estado em `RaceManager`, protegido por lock, alimentado pelo callback da thread de captura.

## Alternativas consideradas

- **Distância mínima até a linha:** simples, mas gera falsos positivos quando o carro passa perto sem cruzar e depende de um limiar difícil de calibrar.
- **Diferença entre frames ou fluxo óptico:** mais robusto para rastrear movimento, porém mais caro e complexo para o escopo atual.
- **Rastreador com Kalman ou ID persistente:** ajudaria em oclusões longas, mas adiciona estado e tuning que ainda não são necessários para três carros com cores fixas.
- **Encerrar apenas manualmente:** reduz o risco de auto-finalização errada, mas piora a experiência e não atende ao fluxo automático desejado.

## Consequências

- Positivas: implementação pequena e determinística; funciona com linha horizontal ou diagonal; resiste a oscilação do centroide; evita chegada dupla; o tempo reflete o primeiro frame de cruzamento.
- Negativas: a confirmação adiciona alguns frames de latência ao ranking; oclusões exatamente sobre a linha podem atrasar ou perder a chegada; a margem nas pontas pode ignorar cruzamentos muito próximos das extremidades.
- Mitigações: `confirm_frames` configurável, ROI para reduzir ruído, área mínima para ignorar blobs pequenos e encerramento manual como saída para carros que não chegam.
- Reavaliar se o projeto passar a usar dois carros da mesma cor ou oclusões frequentes: nesse caso, um rastreador com ID persistente passa a ser necessário.
