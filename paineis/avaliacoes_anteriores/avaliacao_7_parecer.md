# Avaliação independente (7ª) do benchmark Sismo

As correções da 6ª avaliação estão certas. Mas consegui passar telas adulteradas pela auditoria por três caminhos, e achei um erro de tradução que nenhuma checagem vê. Nenhum deles muda o 10 de 18.

O que rodei. Extraí os dois zips, criei um venv com numpy e rodei tudo em Python 3.13 no Windows, sem `-X utf8` no processo pai.

Não fiz:

- Não refiz o render dos PNG (sem Playwright). Só abri `03_Scorecard-en.png` e conferi o texto contra o HTML.
- Não reexecutei detector nem concorrentes.
- Não reproduzi o teste AR(1) do parecer 2.

## 1. Correções da 6ª avaliação: certas

- `numeros.json`: sai idêntico em bytes, com LF, e a auditoria dá 0 problemas com `publication` e `lives`.
- Testes de mutação: `teste_mutacao.py` dá 27 de 27 e `teste_exaustivo.py` dá 0 sobreviventes (1.048 números e 523 pares).
- `rows.json`: refiz do zero com `metrics.rows` e saiu igual às 26 linhas, com diferença máxima de 7e-15. A 6ª avaliação não tinha feito isso.
- Células da tabela: reimplementei a regra de cada célula direto do `rows.json`, sem usar o `numeros_das_telas.py`. Dá 0 divergências fora da regra de exibição declarada (item 44).
- Item 3 (M3): confere nos dados.
  - As 525 ocorrências de "virou o normal novo" caem todas em múltiplos de 100.
  - Os 15 alvos são 8 + 4 + 3, com 8, 2 e 0 acertos.
  - Há 4 registros distintos nas vidas normais e 6 no total.
  - O minuto 38.800 coincide em duas vidas de sementes diferentes.
  - A vida embaralhada tem mudanças de regime reais: o gerador só tira os ciclos do calendário, então os 3 alvos dela são alcançáveis.
- Outros números das ressalvas que conferi e batem:
  - item 7: 308/480, 6,17%, a série `sea_gradual` sem aviso e a `slow_abrupt` com campo errado;
  - item 28: 43 alcançáveis + 29 fora de alcance = 72 eventos;
  - item 10: 681 a 815 min;
  - nulos de S7 do WATCH e do CTM;
  - 5,15 / 3,11 / 2,20 e 2,48 / 0,63 / 0,54.
- Hashes: a soma da `frozen_publication.sha256` confere com os arquivos, e o `ed41901c` é o sha256 de `frozen_approval_original.sha256`.

## 2. O que passa pela auditoria

1. Os PNG não estão protegidos de verdade. `confere_prints.py` aceita até 0,1% de pixels diferentes. Troquei "0,996" por "0,999" no `03_Scorecard-en.png`: deu 0,021% de pixels diferentes e código de saída 0. Um dígito trocado cabe folgado no limiar; só a saída "0 pixel" do pacote mostra que, ali, não houve troca. A auditoria nunca lê os PNG.
2. Sem as pastas `publication` e `lives`, o universo é aceito sem conferência. O universo são as séries, o S7, o S3 por tipo e o M3. Adulterei o `numeros.json` (2.147 séries, 170/200 no S7, "269 de 270" virando 240, 9 registros no M3) e gerei as telas com ele. A auditoria deu 0 problemas e código 0, só com um aviso impresso. Com as pastas, ela pega. O teste de mutação roda sem as pastas e não tem caso de universo adulterado.
3. `numeros_das_telas.py` não falha com caminho errado. Errei um caminho relativo e ele terminou com código 0 e "universo calculado", com `series: 0`, S7 0/0 e M3 0. Falta um `assert` de que `read()` achou séries e as vidas existem.
4. Chaves de `valores()`: todas apontam para o dado certo, mas algumas só acertam por coincidência.
   - A chave `s4a`, usada em "responder sempre 'subiu' também daria X", é a nota do detector, não a base de comparação. A auditoria só pega porque tem um `1` digitado à mão.
   - `l4_n0` é um 0 digitado, reaproveitado em "a vida deu 0 / devia ser 0" do M4.
   - "todas sobem" é texto fixo, não calculado.
   - Os rótulos de métrica (`F1` ou sensib.) em `ROWS` são escritos à mão. Conferi os 26 e estão certos, mas nada confere.
5. "costume" no lugar de "aquecimento". Aparece em três telas em português: `Placar-pt` e `Proposito-pt` ("o mesmo costume") e `Resultados-pt` ("NAB, costume de 500"). O inglês diz "same warm-up". A paridade só olha números, então ela não vê isso.
6. Fora da auditoria: `marca.png` (o logo) e qualquer texto sem dígito nos moldes.

## 3. Ressalvas e problemas novos

- M2 "6 de 6" tem n efetivo menor. Os incidentes de `normal_s746892` e `sem_defeito_s746892` são idênticos (minutos 13638 a 13683), e o de `sem_deriva` é quase igual (13639 a 13669). São no máximo 4 observações independentes. O item 22 cobre isso, mas as telas mostram "6 de 6" sem ressalva, e M2 é uma das 10 linhas que passam.
- Item 2 diz "os alertas não mudam". Isso só vale até o primeiro reinício de segmento. O reinício cai em outro `s0`, então os alertas de segmentos seguintes podem mudar. Nenhum veredito depende disso, porque o WATCH é inelegível por nulo em S1 e S5.
- Coluna "quando começou" (item 8). Sismo 341/479 (71,2%) contra CUSUM 209/268 (78,0%) são taxas condicionais ao que cada um detectou. Sobre os 480 eventos, o Sismo fica com 71,0% e o CUSUM com 43,5%. O texto dá a condição, mas o item 8 fala só em "o CUSUM continua acima". Vale dar as duas taxas.
- M5: o nulo mede "voltou entre 60 e 240 min depois de abrir", e o alvo é "até 180 min depois de sair do ar". As definições são diferentes. A linha reprova de qualquer jeito, mas não está registrada.
- Frase da tabela: "passa em todas as sintéticas" convive com as linhas de limite L1 a L3, que também são sintéticas. Prefiro "em todas as sintéticas que decidem".
- `estado()` e `esperado_veredito()` têm padrões diferentes para status desconhecido (um mostra "limite confirmado", o outro "limite não medido"). Não dispara nos dados atuais.

## O que eu corrigiria antes da v2

- Exigir 0 pixel de diferença no `confere_prints.py`, ou comparar por bloco.
- Fazer a auditoria sair com código diferente de 0 quando falta `publication`.
- Acrescentar ao teste de mutação um caso de universo adulterado.
- Derivar as chaves `s4a`, `l4_n0` e os rótulos de métrica dos dados.
- Corrigir "costume".

Os scripts usados (célula independente, PNG adulterado, universo adulterado) não foram gravados no pacote.
