# Especificação — toy-car-race-vision

## 1. Objetivo

Construir uma aplicação local que usa a webcam do notebook, posicionada na linha de chegada, para identificar carrinhos de brinquedo por cor, determinar a ordem de chegada em cada corrida e exibir os tempos em uma interface visual agradável.

## 2. Público e contexto

- Uso pessoal, educacional ou de demonstração (feira, aula, vídeo).
- Operação por uma pessoa: posiciona a câmera, calibra a linha, sorteia os carros, clica em "Iniciar" ao soltar os carrinhos e acompanha o resultado.
- Ambiente com fundo neutro e iluminação razoavelmente estável.

## 3. Escopo

### 3.1 Dentro do escopo

- Captura de vídeo de uma webcam local.
- Detecção de carros por cor: vermelho, verde, azul e rosa.
- Sorteio de 3 cores por corrida, sem repetição.
- Calibração da linha de chegada por 2 cliques.
- Registro de ordem de chegada e tempo de chegada de cada carro.
- Interface local com vídeo, ranking, tempos, diferença para o 1º, progresso por carro e pódio.
- Som de chegada sintetizado no navegador, com opção de desligar.
- Modo tela cheia para o painel de vídeo e layout responsivo para celular.
- Modo de diagnóstico para ajuste das máscaras de cor.
- Persistência de configuração em arquivo local.

### 3.2 Fora do escopo

- Identificar dois carros da mesma cor.
- Velocidade absoluta em cm/s ou km/h.
- Tempo total de prova medido desde a largada real.
- Gravação de vídeo das corridas.
- Múltiplas câmeras, dispositivos móveis ou acesso pela rede.
- Autenticação, multiusuário ou banco de dados.
- Treinamento de modelo de machine learning.

## 4. Requisitos funcionais

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RF01 | Capturar vídeo da webcam configurada e exibir ao vivo na interface | Alta |
| RF02 | Desenhar sobre o vídeo a linha de chegada e a área de interesse (ROI) | Alta |
| RF03 | Calibrar a linha de chegada com 2 cliques e persistir a calibração | Alta |
| RF04 | Permitir ajuste das faixas HSV de cada cor com visualização das máscaras | Alta |
| RF05 | Sortear 3 cores entre as 4 disponíveis, sem repetição | Alta |
| RF06 | Exibir a formação sorteada antes da largada e permitir novo sorteio | Média |
| RF07 | Iniciar a corrida por um botão, registrando o instante t0 | Alta |
| RF08 | Detectar os carros e classificar a cor de cada um | Alta |
| RF09 | Detectar o cruzamento da linha, no máximo uma vez por carro | Alta |
| RF10 | Montar o ranking pela ordem de cruzamento | Alta |
| RF11 | Exibir tempo de chegada de cada carro e diferença para o 1º, com resolução de milésimos | Alta |
| RF12 | Exibir pódio animado ao final da corrida | Média |
| RF13 | Resetar a corrida para uma nova bateria | Média |
| RF14 | Oferecer modo de diagnóstico com máscaras e métricas de detecção | Média |
| RF15 | Tolerar oclusão parcial usando memória da última posição e histerese | Média |
| RF16 | Exibir barra de progresso por carro durante a corrida | Média |
| RF17 | Emitir som de chegada e fanfarra final, com controle de ligar/desligar | Baixa |
| RF18 | Permitir assistir ao vídeo em tela cheia | Baixa |

## 5. Requisitos não funcionais

| ID | Requisito |
| --- | --- |
| RNF01 | Exibir vídeo a 25–30 fps e processar detecção a pelo menos 15 fps em 960x540 na CPU |
| RNF02 | Refletir um cruzamento na interface em menos de 500 ms |
| RNF03 | Operar por pelo menos 60 segundos contínuos sem travar ou perder a câmera |
| RNF04 | Escutar apenas em localhost, sem dependência de internet |
| RNF05 | Configuração por arquivo, sem necessidade de alterar código |
| RNF06 | Interface e documentação em PT-BR |
| RNF07 | Funcionar em Windows 10/11 com webcam integrada ou USB |
| RNF08 | Não exigir Node.js, React ou build de front-end |
| RNF09 | Código organizado em módulos pequenos e testáveis |
| RNF10 | Tela principal em Bento Grid claro, com fontes locais e movimento reduzido quando solicitado pelo sistema |

## 6. Regras de negócio

- **RN01:** a cor identifica o carro; existe no máximo um carro de cada cor por corrida.
- **RN02:** cada corrida usa exatamente 3 carros, sorteados sem repetição entre as 4 cores.
- **RN03:** a chegada de um carro é contada uma única vez por corrida.
- **RN04:** o tempo de chegada é `instante do cruzamento - instante do clique em Iniciar`.
- **RN05:** o ranking usa o instante do cruzamento; empates são resolvidos pela precisão do timestamp.
- **RN06:** sem escala física, o sistema não exibe velocidade absoluta.
- **RN07:** a linha calibrada vale para a resolução de processamento e é reescalada para a imagem exibida.

## 7. Fluxo de uso

1. Abrir a interface local.
2. Conferir o vídeo e, se necessário, abrir o setup para ajustar câmera, ROI, linha e cores.
3. Calibrar a linha de chegada com 2 cliques e salvar.
4. Sortear 3 carros; a formação aparece na tela.
5. Posicionar os carrinhos e clicar em "Iniciar" no momento da largada.
6. Os carros cruzam a linha; o sistema registra chegadas e atualiza o ranking.
7. Ao final, a interface mostra o pódio, os tempos e as diferenças, com som de chegada.
8. Opcionalmente, usar **Tela cheia** ou duplo clique no vídeo durante a apresentação.
9. Clicar em "Resetar" para a próxima corrida.

## 8. Critérios de aceite do MVP

- [x] A interface abre em `http://127.0.0.1:5000` e exibe o vídeo ao vivo com a linha desenhada.
- [x] A calibração por 2 cliques persiste após reiniciar o servidor.
- [x] O sorteio escolhe 3 cores distintas e é exibido antes da largada.
- [x] O botão "Iniciar" zera os tempos e inicia a corrida.
- [x] Cada carro tem sua chegada registrada uma única vez e na ordem correta.
- [x] Tempo e diferença para o 1º são exibidos com resolução de milésimos.
- [x] O pódio animado aparece ao final, com até 3 finalistas.
- [x] O progresso de cada carro é exibido durante a corrida.
- [x] O som de chegada pode ser ligado ou desligado e a preferência é mantida.
- [x] O painel de vídeo entra e sai da tela cheia.
- [x] A interface não apresenta rolagem horizontal em viewport de 390 px.
- [ ] O sistema roda 60 segundos sem travar com a webcam real.

## 9. Glossário

- **ROI:** região de interesse da imagem onde a detecção é aplicada.
- **HSV:** espaço de cor (matiz, saturação, valor) usado para segmentar cores.
- **Máscara:** imagem binária que marca os pixels de uma cor.
- **Histerese:** exigência de confirmação em mais de um frame para evitar falsos positivos.
- **Confirm frames:** número de frames consecutivos do novo lado da linha necessários para confirmar a chegada.
- **Heat/bateria:** uma corrida completa com 3 carros.
- **t0:** instante do clique em "Iniciar".
