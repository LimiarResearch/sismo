# Ressalvas conhecidas (18/10/2026, depois da 7ª avaliação)

Sete avaliações independentes já examinaram este material; os relatórios estão em `avaliacoes_anteriores/`. Esta lista junta tudo o que elas apontaram e diz a situação de cada ponto. A coluna "origem" diz qual avaliação levantou o ponto (1 a 7); "auditoria" marca o que a auditoria por script das telas achou (ver `gerador/`).

Situações:
- **telas**: já corrigido ou declarado nas telas (`prints/`);
- **repositório pendente**: ainda não está no GitHub nem no cartão do Hugging Face. O repositório deste pacote é a versão anterior às avaliações; as mudanças entram de uma vez no fim da revisão, sem alterar os arquivos congelados nem a rodada arquivada;
- **v2**: exige rodada nova, sob um protocolo novo congelado antes de rodar. Esta rodada fica preservada como está.

## Defeitos no código do benchmark (adaptadores e métricas)

| # | ponto | origem | situação |
|---|---|---|---|
| 1 | CJSD não consegue avisar sem resposta: a calibração deixa `tau` vazio e o ramo de entrada só roda quando `tau` existe (`competitors/methods.py`, função `cjsd`). Os zeros do CJSD nas bases públicas e na empresa não são medida. | 2 | telas (‡ nas 8 células); repositório pendente; v2 |
| 2 | O adaptador ponderado do WATCH ajusta a escala com a série inteira e usa itens futuros no começo do alvo (`_watch_segment`). A comparação não é estritamente causal nas linhas com resposta. O defeito só afeta os p-valores depois do primeiro alarme de entrada: até o primeiro reinício de segmento os alertas não mudam; depois dele o segmento seguinte começa em outro ponto, e os alertas desses segmentos podem mudar. Nenhum veredito depende disso, porque o WATCH já é inelegível pelo nulo em S1 e S5. | 2, 3, 7 | telas (‡ nas 6 células); repositório pendente; v2 |
| 3 | M3 aceita o mesmo registro de "novo normal" para várias mudanças do mesmo campo: os 10 acertos se apoiam em 6 registros distintos, contados por vida. O que entra nos 15 alvos: 8 nas três vidas normais (8 acertos, em 4 registros), 4 nas duas variantes da primeira vida, sem defeito e sem deriva (2 acertos), e 3 na vida de calendário embaralhado (0 acertos). As variantes têm a mesma semente da primeira vida e repetem a mudança de regime do minuto 12.436, por isso o registro do minuto 18.600 aparece nelas; isso é dependência real. A vida embaralhada é a empresa com o calendário sorteado em blocos (sem ciclo de hora, de dia ou de mês) e com mudanças de regime reais: os 3 alvos dela podiam ser acertados, e o detector não acertou nenhum. O detector só registra "virou o normal novo" em minutos múltiplos de 100 (as 525 ocorrências na rodada), então registros de vidas independentes coincidem no mesmo minuto por causa dessa grade (38.800 na rota de notas fiscais em duas vidas); contar por rota e minuto, como uma versão anterior deste item fazia (3 registros), junta registros independentes. Nas três vidas normais são 4 registros. | 2, 5, 6 | telas (nota na linha e no placar, "6 registros distintos"); repositório pendente; v2 (associação exclusiva, vidas independentes) |
| 4 | Ranking: a primeira versão não aplicava o teto aos concorrentes nas tarefas sintéticas; depois de corrigido, continuava dependente do CJSD quebrado e era um resumo posterior, não critério do protocolo. | 1, 2 | a tela de ranking foi retirada; volta na v2, se for pré-especificada |
| 25 | A tabela completa marcava com † oito métodos elegíveis em S5 (aplicava alerta e log juntos; o protocolo usa só o teto de alerta nessa linha). Mesmo erro de origem do ranking: o gerador das telas, não o código do benchmark. | 3 | telas (corrigido: S5 aparece como empate com os métodos por campo, como no placar) |

### Por que nenhum veredito de linha depende de 1, 2 ou 3

- **CJSD.** P1, P5 e M1 já perdem para concorrentes sem ‡ (HDDM_W, teste por campo, matrix profile); um CJSD corrigido só poderia subir o melhor concorrente. P4, P4o e P6 reprovam pelo nulo do próprio Sismo: o nulo combinado (treino e cópias embaralhadas), que é o que o protocolo compara com o teto 0,1, dá 2,48 por 1.000 itens em P4 e P4o (SMD) e 0,54 em P6 (MSL); P5 (SMAP) dá 0,63. Só no treino, as taxas são 5,15 (SMD), 3,11 (SMAP) e 2,20 (MSL). Uma versão anterior desta lista comparava as taxas só do treino com o teto e atribuía o 3,11 a P4o; corrigido depois da 5ª avaliação. Em M2 o Sismo tem 1,000 e não pode perder. Nenhuma linha que passa tem um CJSD ‡ capaz de derrubá-la.
- **WATCH.** Em S1 (0,996) e S5 (1,000) o Sismo não pode perder. S2 é a única exposta: um WATCH corrigido precisaria de F1 de log acima de cerca de 0,95 e ficar sob o teto de 5% de nulos. Na rodada arquivada o WATCH escreve log em 368 a 370 das 370 séries nulas, e o CTM, que não tem adaptador ponderado nenhum, faz o mesmo (369 a 370 de 370). A inelegibilidade vem da regra de Shiryaev-Roberts com limiar 10⁴ em séries de 18 mil itens, cujo tempo médio até alarme falso é da ordem do comprimento da série, e não do defeito. Por isso "o WATCH está acima do teto e não decide" continua válido depois da correção.
- **M3.** Continua acima do nulo zero mesmo contando só registros distintos.

O 10/18 é o da rodada arquivada; a confirmação definitiva é a da v2.

### Como ler o 10 de 18

| tipo | linhas |
|---|---|
| vitória sobre concorrentes | S1, S2 |
| vitória por capacidade | S3: o protocolo marca WON, mas nas 210 mudanças de entrada, as únicas em que os concorrentes pontuam, o ADWIN faz 210/210 e o Sismo 209/210; a vitória vem das 270 quebras de relação, onde os métodos por campo não podem pontuar |
| empate | S5 (com os métodos por campo), M2 (com DDM, HDDM_A e HDDM_W, todos 6/6) |
| contra o nulo ou o teto, sem concorrente | S4a, S4b, S4c, S7, M3 |

S5 empata com 9 métodos, vários que nunca alertam, para os quais "sem alerta" é automático. M2 empata com erro-padrão zero (todos com 6/6), o caso degenerado do critério. S4a nem discrimina: responder sempre "subiu" também daria 1,000. M1 reprovou por margem estreita: 0,300 de diferença contra 2 erros-padrão de 0,284, com 10 episódios de 3 vidas. Outra semente de reamostragem poderia dar empate, e o resultado iria a 11 de 18, ainda reprovado. As telas mostram a decomposição no veredito; a margem de M1 fica registrada aqui.

## Alcance das linhas e das telas

| # | ponto | origem | situação |
|---|---|---|---|
| 5 | S4a (direção): a resposta certa é fixa nos 209 casos avaliados: em 179 (campos numéricos) a regra de `metrics/rows.py` conta "subiu" como certo, e nos 30 categóricos conta como certo a categoria 0 ganhar participação. Uma resposta constante também faria 1,000. A linha não testa quedas. Versões anteriores diziam "as 209 mudanças sobem", o que não descrevia os 30 casos categóricos. | 1, 2, 3, 7 | telas (contagem calculada das saídas); repositório pendente; v2 (subidas e quedas, categorias variadas) |
| 6 | S4b (tamanho): lido 500 itens depois do aviso, condicionado a um aviso válido e ao primeiro campo verdadeiro com relato; não é o tamanho no instante do aviso. | 1, 2 | telas; repositório pendente; v2 |
| 7 | S3 (onde): acerto quando todo campo acusado é verdadeiro; não exige achar todos. Igualdade exata do conjunto: 308/480; em `ramp_all` (20 campos mudam), cobertura média de 6,17%. Os erros: 1 série sem aviso (`sea_gradual`) e 1 com campo errado. | 1, 2, 3 | telas ("todo campo que ele cita mudou"); os números 308/480 e 6,17% ficam aqui e no README; repositório pendente; v2 (precisão e cobertura) |
| 26 | S3 (onde), teto dos concorrentes: os métodos por campo só emitem log e não veem a resposta, então só pontuam nas 210 mudanças de entrada; as 270 quebras de relação só contam com alerta. Os 43,75% do ADWIN são 210/210 nas entradas e 0/270 nas relações (o teto aritmético 7/16). O Sismo faz 209/210 e 269/270. A diferença na linha é de capacidade, não de qualidade de localização. | 3 | telas (placar aberto em entradas e relações; nota na legenda das telas de recursos e da tabela completa) |
| 8 | "Quando começou": Sismo 341/479 mudanças detectadas, tolerância de 500 itens. O 96,9% que as telas mostravam para o CUSUM (439/453) juntava duas configurações acima do teto: a de S1 alerta em 370 das 370 séries nulas, a de S2 escreve log em 370 das 370. Com as mesmas configurações da tabela completa, o CUSUM faz 209/268 (78,0%), com † porque a de S1 passa do teto. Essas taxas são condicionais ao que cada método detectou; sobre as 480 mudanças de S1 e S2, o Sismo acerta o começo em 341 (71,0%) e o CUSUM em 209 (43,5%). Na taxa condicional o CUSUM fica acima; sobre o total, o Sismo. Entre os concorrentes, só o CUSUM e o matrix profile estimam o começo; nos outros, o "quando" do rows.json é só o instante do aviso. | 2, 3, 4, 7 | telas (78,0% †, e as duas taxas sobre o total na legenda) |
| 9 | A coluna "trajetória" era só o novo normal dos degraus sintéticos (S4c); a volta ao normal reprova (M5) e a deriva da carteira reprova (M4). | 2 | telas (coluna renomeada) |
| 10 | Volta ao normal: 5 de 7 observadas em 11 a 14 h (681 a 815 min); 0 de 7 em até 3 h. O relógio conta a partir do momento em que o defeito sai do ar (`metrics/rows.py`, "after the defect goes off the air"), ou seja, depois da recuperação; o rótulo da linha no repositório diz "after the outage", que é ambíguo. | 2, 3 | telas; repositório pendente (rótulo explicado no README) |
| 11 | Nulos sintéticos: 0/370 com alerta e 6/370 com log; não incluem nulos estacionários autocorrelacionados. | 2, 3 | telas (placar e linha S7 da tabela) |
| 12 | "O único que responde a tudo" vale para os métodos e adaptadores deste benchmark, como formatos de saída implementados; não é exclusividade no campo inteiro nem qualidade provada em todas as dimensões. O CUSUM ganha a coluna "quando", então o título vale como cobertura, não como qualidade. | 1, 2, 4 | telas (título "devolve tudo", subtítulo "a coluna mostra o que cada método devolve, não quem faz melhor"); repositório pendente (trabalhos relacionados) |
| 13 | L4 de SMD ("limite não confirmado"): o Sismo acha 9/127 eventos curtos; o único concorrente permitido é o CJSD ‡, então o rótulo depende do defeito. Nas linhas de limite o nulo do detector não é aplicado, por isso o Sismo aparece sem † ali e com † em P4. | 2, 3 | telas (9 de 127 na legenda; ‡ no veredito); repositório pendente |
| 14 | O F1 por evento usa janelas próprias (vários avisos numa janela contam um evento; janelas estendidas em SMD, SMAP e MSL); não é comparável com F1 por ponto de outros trabalhos. Com avisos restritos à duração marcada, o F1 do Sismo cai de 0,063 para 0,045 em SMD, de 0,091 para 0,083 em SMAP e de 0,222 para 0,157 em MSL. | 1, 2, 3 | repositório pendente |
| 15 | "Empatou" (diferença dentro de dois erros-padrão) é o critério operacional do protocolo, não um teste de equivalência. Em M2 o empate vem de erro-padrão zero (todos com 6/6), o caso degenerado. | 2, 4 | repositório pendente |
| 27 | Legenda da tabela completa: a célula mostra a melhor configuração abaixo do teto, e só leva † quando nenhuma está abaixo (por exemplo, WATCH em P1 mostra 0,235; a configuração de 0,282 tem nulo 0,114). | 3 | telas (legendas reescritas na tabela e em recursos) |
| 28 | NAB "24 de 43": 43 é o número de eventos alcançáveis depois do aquecimento, em 30 séries; 12 eventos ficam dentro do aquecimento e 6 das 36 séries são menores que ele. O conjunto tem cerca de 72 eventos (linha P1c: 66 em 36 séries com aquecimento de 500, mais 6 fora de alcance). | 3 | telas ("entre os que ficam depois do aquecimento"); repositório pendente (README) |
| 29 | Intervalos binomiais das linhas pequenas: 7/10 vai de cerca de 35% a 93%; 10/15, de 38% a 88%. | 1, 3 | repositório pendente |

## O detector

| # | ponto | origem | situação |
|---|---|---|---|
| 16 | Autocorrelação: em séries estacionárias AR(1), sem mudança, o detector escreve logs (dezenas a centenas por série com rho alto) e nenhum alerta. Os nulos do protocolo não cobrem esse caso. | 1, 2, 3 | telas (Propósito, placar e tabela); repositório pendente; v2 (nulos autocorrelacionados e sazonais; tratamento no detector) |
| 17 | Bases públicas: os avisos a mais no trecho de treino podem ser mudanças sem rótulo ou reação à autocorrelação; nenhuma das duas está demonstrada, e o zero nas cópias embaralhadas não separa as duas. | 1, 2 | telas (as duas hipóteses); repositório pendente |
| 18 | Os "e-values" do detector são fatores de Bayes com reinício quando a evidência fica não positiva; não são e-values no sentido estrito, e A = 200.000 não dá a garantia 1/A de alarme falso. O nome também está nos comentários do código e no protocolo. | 1, 2 | repositório pendente (nota no README; o código congelado não é editado); v2 |
| 19 | A recomendação "retreinar se a regra quebrou, manter se só a entrada mudou" e o uso "ao lado de um detector de anomalia" não foram testados. | 1, 3 | telas (as duas frases qualificadas como uso pretendido, não testado); repositório pendente |
| 30 | Eixo de erro: os concorrentes desse eixo monitoram o erro de um modelo online; o Sismo usa a sua própria referência discretizada. As entradas não são idênticas. | 1, 3 | repositório pendente |

## Desenho e documentação

| # | ponto | origem | situação |
|---|---|---|---|
| 20 | Cronologia: houve uma rodada de desenvolvimento (protocolo v1) antes da aprovação (protocolo v2). "Congelado antes de qualquer rodada" é impreciso; o certo é "protocolo de aprovação congelado antes da rodada de aprovação". Também: a aprovação rodou com duas paradas e retomadas e foi rodada de novo por inteiro em 14/10 com o código de publicação, com resultado idêntico; "rodada uma vez" saiu das telas. | 2, 3 | telas; repositório pendente (o README do GitHub e o cartão do Hugging Face ainda dizem "before any run") |
| 21 | O hash prova conteúdo, não data; o pacote não traz o código original em português arquivo por arquivo nem uma referência pública datada do congelamento. | 1, 2 | repositório pendente (tag imutável da versão original e referência datada) |
| 22 | A empresa simulada tem três vidas e variantes da primeira; processos, episódios e o incidente repetido nas variantes não são observações independentes; intervalos binomiais não capturam essa dependência. | 1, 2 | repositório pendente; v2 (mais vidas independentes) |
| 23 | As 2.047 séries incluem cópias embaralhadas, variantes de aquecimento e processos da mesma vida; não são 2.047 bases independentes. | 1 | repositório pendente |
| 24 | O título da tela "Por que ele não passa nos benchmarks clássicos" soa mais conclusivo que os dados; o texto da tela já traz as hipóteses. | 2, 3 | título mantido; texto ajustado |

## Apresentação das telas (4ª avaliação e auditoria)

| # | ponto | origem | situação |
|---|---|---|---|
| 31 | O veredito somava S3 como vitória; ele é vitória por capacidade (ver "Como ler o 10 de 18"). | 4 | telas ("2 vitórias, 1 por capacidade, 2 empates, 5 contra nulo ou teto") |
| 32 | A coluna "quando começou" não aplicava o teto (ver item 8). | 4 | telas |
| 33 | A métrica das linhas não estava dita: S3, S5, M1, M2, P4o e as linhas L4 são sensibilidade, não F1. Em P4L4 o 0,071 é 9/127 de sensibilidade; com 2.525 avisos falsos o F1 ali é 0,007. Nas linhas de limite o protocolo não aplica o nulo do Sismo, por isso ele não leva † ali, embora leve em P4. | 4 | telas (métrica no rótulo de cada linha; P4L4 e a regra das linhas de limite na legenda) |
| 34 | O gerador das telas não estava no pacote, e o rodapé dizia "um comando reproduz cada número". Depois, a auditoria foi uma lista de checagens escritas à mão, e cada avaliação achou um tipo de número fora da lista: na versão 5, 9 de 11 erros plantados passaram; na versão 6, 88 de 523 pares de números mudados nos dois idiomas passaram (colunas de recursos não lidas, células do Sismo sem concorrente, parâmetros dos rótulos, hash, cabeçalho das colunas, folga de arredondamento). Na versão 7, ainda passavam: PNG com um dígito trocado (a comparação aceitava 0,1% dos pixels), universo adulterado quando a auditoria rodava sem as pastas publication e lives, um caminho errado para as saídas (o script terminava com universo zerado), um erro de tradução sem número ("costume" no lugar de "aquecimento") e o logo. | 4, 5, 6, 7 | o desenho mudou: `gerador/telas.py` gera as oito telas, com cada número visível vindo de um valor calculado (rows.json, numeros.json, metrics/rows.py, protocol/seeds.json ou os rótulos das linhas) e para se sobrar dígito visível sem fonte; `gerador/auditoria.py` recalcula o numeros.json, roda o gerador e exige que cada tela publicada seja igual, byte a byte, à gerada, além das conferências independentes de antes; os testes exaustivos da 6ª avaliação (1.048 números num idioma, 523 pares nos dois) e as mutações dirigidas dela dão 0 sobreviventes; rodapé "um comando reproduz as linhas; estas telas derivam delas" | Depois da 7ª avaliação: `confere_prints.py` exige 0 pixel de diferença; sem as pastas, a auditoria reporta problema, a menos que se peça `--parcial` de propósito; `numeros_das_telas.py` para se não achar saídas ou vidas e confere o universo contra as linhas (S7, S3, M3, S4a, M2); a auditoria confere 11 termos técnicos entre inglês e português e o sha256 do logo; o teste de mutação tem 32 casos, inclusive universo adulterado, tradução trocada, texto sem número e logo |
| 35 | S7: as 370 séries sem mudança são 180 séries nulas (6 famílias × 30) e 190 cópias embaralhadas. | 3, 4 | telas (placar e tabela) |
| 36 | O subtítulo da tela de recursos dizia "toda coluna medida", e as células ‡ não são medida. | 4 | telas ("cada coluna da rodada de aprovação") |
| 37 | S5 empata com 9 métodos (inclusive CJSD e isolation forest), não só com os por campo, e para os que nunca alertam o "sem alerta" é automático. | 4 | telas |
| 38 | O XOR aparecia na coluna "não passa" do placar, mas é uma linha de limite que não decide; L1, L2 e o L4 do SMD não apareciam. | 4 | telas (seção "limites declarados (não decidem)" no placar) |
| 39 | O rodapé ("congelado antes", ed41901c) lia como prova de cronologia; o hash prova conteúdo, não data (ver item 21). | 4 | telas ("sha256 ed41901c, que prova o conteúdo, não a data") |
| 40 | O placar mostrava a taxa de avisos do Sismo só no trecho de treino (2,2 a 5,1 por 1.000 itens) ao lado do teto 0,1, mas o teto se aplica ao nulo combinado, treino mais cópias embaralhadas, que dá 0,5 a 2,5. As duas passam do teto; o veredito não muda. | auditoria | telas ("com as cópias embaralhadas (0 nelas): 0,5 a 2,5, teto 0,1") |

## 5ª avaliação

| # | ponto | origem | situação |
|---|---|---|---|
| 41 | Seleção da melhor configuração com os dados da aprovação: cada célula de concorrente mostra a melhor de duas configurações (a padrão e a ajustada num conjunto separado), escolhida depois de ver o resultado da rodada; o Sismo tem uma configuração só. É conservador para as vitórias do Sismo, mas pesa nas linhas perdidas ou empatadas (M1 perde por 0,300 contra 2 erros-padrão de 0,284). O protocolo faz o mesmo ao escolher o melhor concorrente da linha. | 5 | repositório pendente; v2 (configuração dos concorrentes fixada antes da rodada) |
| 42 | M4 no placar: "2 de 3 vidas · uma vez na vida sem deriva" não dizia que a linha falha por dois motivos (uma vida normal com 0 e a vida sem deriva com 1, quando devia ser 0). | 5 | telas ("2 de 3 vidas normais · uma vida normal deu 0, e a vida sem deriva também disparou uma vez (devia ser 0)") |
| 43 | Gerador: listas escritas à mão (`DETECTOR_FORA`, `DEFEITO`, `COM_CONCORRENTE`), o † do detector não calculado, fatos de texto que assumiam o mínimo e o máximo, o "209/210 e 269/270" escrito como texto, e `open()` sem codificação (quebra no Windows). | 5 | `DETECTOR_FORA` e `COM_CONCORRENTE` saem do `rows.json`; os tetos saem de `metrics/rows.py`; o † do detector sai do status da linha; mínimo, máximo, empates e S3 por tipo são calculados; `encoding="utf-8"` em todos os arquivos; a lista do ‡ continua escrita à mão, a partir da leitura de `competitors/methods.py`, e está dita no script |
| 44 | Regra de exibição que não é do protocolo: quando a melhor configuração elegível de uma família vale 0 e outra dela pontua, a célula mostra a que pontua, com †. O protocolo escolhe só o melhor global da linha. | 5 | dito no script e na legenda; o script confere, linha por linha, que o maior valor elegível é o `best_value` do protocolo, e para se não for |
| 45 | Os PNG em `prints/` não são conferidos contra o HTML: a auditoria lê o HTML; os PNG são capturas desse HTML com Chromium. | 5 | `gerador/render_prints.mjs` renderiza o HTML de novo e `gerador/confere_prints.py` compara pixel a pixel com `prints/` (nesta versão, 0 pixel diferente nas 8 telas); exige Node e Playwright |
| 46 | A reprodução do `rows.json` pelas avaliações 1 e 5 foi em Windows com Python 3.13; o ambiente original era Linux com Python 3.11.17. As diferenças ficaram abaixo de 1e-9. | 5 | registrado |

## 6ª avaliação

| # | ponto | origem | situação |
|---|---|---|---|
| 47 | O teste de mutação contava "pegou" sempre que a auditoria saía com código diferente de 0, inclusive quando ela quebrava; e no Windows só rodava com `-X utf8`, porque a saída dos processos filhos saía em cp1252. | 6 | o teste exige código 1 e "problemas: N" com N > 0, e conta quebra como falha; os scripts reconfiguram a saída para UTF-8 e chamam os filhos com `-X utf8`; os arquivos são gravados com fim de linha LF |
| 48 | O gerador da tabela também reescrevia o `canvas.json` com uma posição antiga das telas, que deixou um vão no canvas publicado desde a versão 27. | auditoria | corrigido no canvas (versão 30); o gerador novo não mexe no canvas |

## 7ª avaliação

| # | ponto | origem | situação |
|---|---|---|---|
| 49 | M2 "6 de 6": os 6 incidentes estão em 6 vidas, mas 4 delas são da mesma semente; nas duas variantes e na vida normal dessa semente o incidente é o mesmo (minutos 13.638 a 13.683, e 13.639 a 13.669 na sem deriva), e o da vida embaralhada cai em outro minuto. São no máximo 4 incidentes independentes, contados como mesma semente e começo a menos de 60 minutos. M2 é uma das 10 linhas que passam. | 7 | telas ("no máximo 4 independentes" no placar, calculado); v2 (mais vidas independentes, ver item 22) |
| 50 | M5: o nulo mede "voltou entre 60 e 240 minutos depois de abrir" e o alvo é "voltou até 180 minutos depois de o defeito sair do ar"; as duas definições não são a mesma. A linha reprova dos dois jeitos. | 7 | repositório pendente; v2 (nulo com a mesma definição do alvo) |
| 51 | Chaves que acertavam por coincidência no gerador: a base de comparação do S4a usava a nota do detector; um 0 digitado servia a três frases diferentes; "todas sobem" era texto fixo; os nomes de métrica dos rótulos eram escritos à mão. | 7 | a base do S4a sai da contagem das saídas; cada 0 tem chave e fonte próprias (regra da caixa de latão, mínimo do M4, "never" do rótulo do M4, n das linhas L4); "todas sobem" virou a contagem calculada; o nome da métrica sai do campo `metric` do `rows.json`, e o gerador para se um rótulo e a linha discordarem |
| 52 | "costume" no lugar de "aquecimento" em três telas em português. | 7 | corrigido; a auditoria agora confere termos técnicos entre os idiomas |
| 53 | A frase da tabela "passa em todas as sintéticas" não excluía as linhas de limite L1 a L3, que também são sintéticas. | 7 | telas ("que decidem") |
| 54 | `estado()` no gerador e `esperado_veredito()` na auditoria tratavam de jeitos diferentes um status desconhecido. | 7 | os dois agora reconhecem só os status que existem e param ou reportam diante de outro |
