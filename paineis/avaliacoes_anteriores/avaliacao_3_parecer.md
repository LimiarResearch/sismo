# Avaliação independente (3ª) do benchmark Sismo, 18/10/2026

Material: github_sismo_v3.zip e huggingface_sismo-benchmark-runs_v3.zip (pasta paineis/ idêntica nos dois). Parti do paineis/LEIAME.md, li RESSALVAS.md, os dois pareceres anteriores, o protocolo, metrics/rows.py, competitors/methods.py e as 8 telas. Recalculei a partir de results/publication/rows.json e das saídas por série de publication.zip.

Não fiz: reexecutar o detector ou os concorrentes (sem river/scikit-learn aqui); reconferir o M3 (6 registros distintos) nem as vidas simuladas. Aceito esses pontos como a avaliação 2 os documentou.

## Resumo

- Telas vs dados. Os números conferem com rows.json. Há um ponto de substância (S3) e vários de redação/consistência. Detalhes na seção 2.
- Vereditos de linha e os ‡. Concordo: nenhum veredito muda, e o 10/18 não pode subir. Prova na seção 1. Há uma ressalva de fraseado, porque a conta usa "passou = não perdeu".
- Problemas novos. O mais relevante é o teto estrutural de 43,75% dos concorrentes em S3, que as telas apresentam como "44%". Os demais são menores.

## 1. Os ‡ mudam algum veredito?

Regra do protocolo (metrics/rows.py): passa = WON, TIED ou acima do nulo. Só perde (LOST) quem fica abaixo do melhor concorrente elegível por mais de 2 erros-padrão.

Células ‡ do CJSD (P1, P1c, P4, P4L4, P5, P6, M1, M2). Os 18 que decidem:

- P1, P5 e M1 já perdem para concorrentes sem ‡ (HDDM_W, teste por campo, matrix profile). Um CJSD corrigido só poderia subir o "melhor concorrente".
- P4, P4o e P6 reprovam pelo nulo do próprio Sismo (5,15 / 3,11 / 2,20 por mil contra teto 0,1), que não depende do CJSD.
- M2: o Sismo tem 1,000 e não consegue perder. O CJSD corrigido no máximo empata.
- Nenhuma linha que hoje passa tem célula CJSD ‡ capaz de derrubá-la.

Células ‡ do WATCH (S1, S2, S5, L1, L2, L3; só L1 a L3 não decidem):

- S1: o Sismo tem 0,996 com erro-padrão de ~0,027. Para perder, um concorrente precisaria de F1 acima de 1,0. Impossível.
- S5: 1,000 contra 1,000. Impossível perder.
- S2 é a única exposta: 0,929 contra 0,879 do CJSD. Um WATCH corrigido precisaria de log-F1 acima de ~0,95 e ficar sob o teto de nulos de 5%.
- Reforço que as ressalvas não trazem: na rodada arquivada, o WATCH dispara log em 368 a 370 dos 370 nulos. O CTM, que não tem ponderação nenhuma, faz o mesmo (369 a 370 de 370; 190/190 nas cópias embaralhadas). Logo a inelegibilidade do WATCH não vem do defeito ponderado. Provavelmente vem da regra Shiryaev-Roberts 10⁴ numa série de 18 mil itens, que tem tempo médio até alarme falso da ordem do comprimento da série. Isso torna "WATCH acima do teto, então não decide" um argumento válido sob correção. Sugiro escrevê-lo assim em RESSALVAS.md, em vez de só afirmar "acima do teto".
- O defeito ponderado só afeta p-valores a partir do primeiro alarme de entrada. Os alertas (REAL, que exigem alarme anterior a esse ponto) não mudam. Só os logs e os reinícios de segmento mudam.

Conclusão: 10/18 se mantém. As 8 reprovações vêm de causas sem ‡, e as 10 aprovações não têm concorrente ‡ capaz de derrubá-las.

Ressalva de enquadramento. Entre as 10, apenas S1, S2 e S3 são vitórias sobre concorrentes. S5 e M2 são empates (M2 empata com DDM, HDDM_A e HDDM_W, cada um com 6/6). S4a, S4b, S4c, S7 e M3 são contra o nulo ou o teto, sem concorrente. S4a nem discrimina, pois o classificador "sempre subiu" também dá 1,000. "10 de 18" lê-se melhor com essa decomposição ao lado.

Fragilidade de M1. LOST por 0,300 contra 2×0,142 = 0,284, com 10 episódios de 3 vidas. Uma outra semente de reamostragem poderia dar TIED, e o veredito iria a 11/18, ainda "não aprovado". Vale dizer isso, e não que M1 foi perdido de modo claro.

## 2. As telas dizem só o que os dados sustentam?

### 2.1 S3, o "44%" do melhor concorrente (telas 01, 03, 04; PT 05, 07, 08)

Isso é substantivo. Recontei where por tipo de série, nas saídas:

| método | mudanças de entrada (210) | quebras de relação (270) |
|---|---|---|
| Sismo | 209 (99,5%) | 269 (99,6%) |
| ADWIN por campo (δ=1e-6), "melhor concorrente" | 210 (100%) | 0 (0%) |
| teste por campo | 180 (85,7%) | 0 |

- Os 43,75% do ADWIN são exatamente 7/16 (210/480), o teto aritmético. Nas séries de entrada, o ADWIN nomeia um campo verdadeiro em todas e empata ou supera o Sismo.
- O 0,996 contra 0,438 vem inteiro da outra metade. As quebras de relação só valem como acerto com alerta. Os métodos por campo (/field) só emitem log e não veem y, então não têm como pontuar ali.
- Isso é diferença de capacidade, não de qualidade de localização. A tela "diz qual campo mudou… melhor concorrente 44%", e a coluna "onde: campo certo", leem como se os concorrentes localizassem mal.
- Sugestão: mostrar S3 separado em entrada (210) e relação (270), ou dizer "os concorrentes só participam das 210 mudanças de entrada, onde o ADWIN acerta 210/210".

### 2.2 Inconsistência de † em S5 (tela 04)

- O protocolo usa só o teto de alerta em S5 (null_alert). Pelo table.txt, o melhor concorrente é o teste por campo, elegível.
- A tela marca com † (inelegível) Page-Hinkley, CUSUM, EWMA, ADWIN, KSWIN, DDM, teste por campo e isolation forest em S5, e deixa a caixa de latão só em Sismo e CJSD. Ela parece aplicar o critério combinado (alerta e log), que é o de S3.
- A tela 03 diz "empata com os métodos por campo". Isso confere com o protocolo e não com o † da tela 04.
- Sem efeito no veredito, mas é inconsistente com a legenda "† = não pode ganhar a linha".

### 2.3 P4L4 (tela 04)

- O Sismo (0,071) está em caixa de latão e sem †, enquanto em P4 (0,063†) o nulo dele passa do teto. Para linhas-limite o código passa True e não aplica o nulo do detector. A legenda diz "o Sismo inclusive".
- O rótulo "limite não confirmado" continua sem o denominador (9/127) pedido pela avaliação 2.
- O único concorrente elegível é o CJSD ‡ (0,000), então o rótulo depende do defeito. A ressalva 13 diz "‡ no CJSD", mas a coluna de veredito não tem marca.

### 2.4 Ressalvas marcadas como "telas" que só foram resolvidas em parte

- Ressalva 11 (nulos sintéticos) e 16 (autocorrelação). A tela 03 ("fica quieto em séries sem mudança · 0 de 370 · 6 com log") e a linha S7 da tela 04 não dizem que os nulos não incluem séries estacionárias autocorrelacionadas. A avaliação 2 pedia esse texto. A autocorrelação só aparece no texto da tela 02 e no rodapé da tela 04, ligada a SMD/SMAP/MSL. A ressalva 24 mantém o título da tela 02 ("Por que ele não passa…").
- Ressalva 19. Está só como "repositório pendente", mas a tela 02 afirma "retreina se a regra quebrou, mantém o modelo se só a entrada mudou" sem qualificação. "Use ao lado de um detector de anomalia" também não foi testado (ressalva 12 cobre só "único que responde a tudo").
- Ressalva 8 ("quando começou"). O 96,9% do CUSUM é 439/453, que mistura duas variantes: cusum/error em S1 (258/266) e cusum/field em S2 (181/187). A variante de S1 está † na coluna "F1 de alerta" e aqui aparece sem marca. O Sismo é 341/479. Em S2, onde existe início atribuído, o Sismo tem 155/210 (73,8%) e o CUSUM 96,8%. O CUSUM ganha nessa coluna e a tela mostra isso, mas o texto "desde quando" da tela 02 se apoia só nesse número.
- Ressalva 7 (S3). Os números 308/480 e 6,17% estão só no RESSALVAS.md, não nas telas. As telas dizem "todo campo citado é verdadeiro".

### 2.5 Redações que valem ajuste

- Tela 03 e M2. "6 de 6 · 10 de 15" não diz que M2 é empate com DDM, HDDM_A e HDDM_W (cada um com 6/6) e que passa por empate. S5 diz.
- "24 de 43" eventos NAB (tela 02). Dos eventos do conjunto de aprovação, 12 estão fora de alcance pelo aquecimento, e 6 das 36 séries foram descartadas por serem menores que o aquecimento (series 30, oor 12 em rows.json). Pela linha P1c (66 + 6), o conjunto tem cerca de 72 eventos. O denominador 43 é aquecimento-dependente e não aparece nas telas, só o README e a linha P1c.
- Legenda da tela 04. "† = a melhor configuração passa do teto". Na verdade a célula mostra a melhor configuração permitida e só leva † quando nenhuma é. Exemplo: WATCH em P1 mostra 0,235, e a melhor configuração, 0,282, tem nulo 0,114. Sem ‡/† a leitura fica mais frouxa do que parece.
- "aprovação rodada uma vez, 2.047 séries". A aprovação rodou com duas paradas e retomadas, e foi reexecutada inteira em 14/10 com o código de publicação (resultados idênticos). A frase é defensável, mas pode ser lida como "uma única execução em toda a história".
- M5. "11 a 14 h depois da recuperação" nas telas. O registro da aprovação e a linha dizem "depois da queda" ("outage"). A faixa (681 a 815 min) confere, mas confirme a referência do relógio.
- Cronologia. O cartão do Hugging Face (README.md do dataset) ainda diz "The protocol was frozen before any run". A ressalva 20 lista só o README do GitHub como pendente. O HF não está na lista.

### 2.6 O que ficou fora de RESSALVAS.md

Da avaliação 1: a sensibilidade das janelas (F1 cai de 0,063 para 0,045 em SMD, de 0,091 para 0,083 em SMAP e de 0,222 para 0,157 em MSL com avisos restritos à duração marcada); os intervalos binomiais (7/10 ≈ 35 a 93%; 10/15 ≈ 38 a 88%); e a observação de que os concorrentes do eixo de erro usam um modelo online e o Sismo, sua própria referência discretizada. Nada disso muda veredito, mas o LEIAME diz que "tudo o que elas apontaram está consolidado".

## 3. O que conferi e está certo

- ed41901c… é o sha256 de history/frozen_approval_original.sha256. O manifesto de avisos tem 8af1b154…, e o de publicação 7de3ed49…, todos como declarado.
- As 33 sementes (30 sintéticas, 3 da empresa) recalculadas a partir do arquivo congelado batem com seeds.json.
- table.txt e README batem com rows.json. Os totais 10/18, 8 reprovadas, 478/480, 209/209, 179/179, 176/180, 0/370 e 6/370, M3 10/15 com nulo 0/155 e M4 [2,0,1] e [1] conferem. S4c: 6 séries × 30.
- As 8 células ‡ do CJSD e as 6 do WATCH nas telas coincidem com o código: tau=None bloqueia também o ramo de entrada (methods.py:223), e o WATCH ponderado só roda com resposta.
- 308/480 igualdade exata e cobertura de 6,2% em ramp_all (ressalva 7): conferem. O erro de S3 é 1 série sem aviso (sea_gradual) e 1 com campo errado.
- Taxas de nulo no treino: SMD 5,146, SMAP 3,111, MSL 2,200, e 0 nas embaralhadas. NAB 24/43 e 1,96/mil. M5: 5 de 7 em 681 a 815 min.
- Paridade EN/PT: sem divergência de número entre as telas dos dois idiomas.

## 4. Sugestões antes do envio ao GitHub

- Corrigir S3 nas telas 01/03/04 (seção 2.1) e rever o † de S5 e a marca de P4L4.
- Acrescentar "sem nulos estacionários autocorrelacionados" ao texto de S7 e à tela 03.
- Qualificar na tela 02 a recomendação retreinar/manter e o "use ao lado de um detector".
- Atualizar o cartão do Hugging Face (cronologia) junto com o README.
- Em RESSALVAS.md: o argumento do CTM sobre a inelegibilidade do WATCH; a decomposição de 10/18; a fragilidade de M1; os itens da seção 2.6.
