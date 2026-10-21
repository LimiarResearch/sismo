# Avaliação independente (4ª): telas do benchmark do Sismo

Li as 8 telas, o LEIAME, o RESSALVAS e a 3ª avaliação. Recalculei os números a partir de results/publication/rows.json e do código de metrics/rows.py. A pasta `paineis/` é idêntica nos dois zips.

Não reexecutei o detector nem os concorrentes. Também não recalculei todos os † e ‡ célula por célula, só os que tocam os pontos abaixo.

## 1. As correções da 3ª avaliação estão certas?

Sim. Conferi cada uma contra os dados:

- S3. Sismo 209/210 em entradas e 269/270 em relações; ADWIN 210/210 e 0/270. Isso fecha com 478/480 e 210/480 = 43,75%. O "44%" saiu e a legenda explica o teto.
- S5. O † saiu e a linha aparece como empate. Isso bate com o protocolo, que usa só o teto de alerta nessa linha.
- P4L4. 9/127 está nos dados, e o ‡ no veredito está correto.
- S7 e placar. Dizem agora que os nulos não incluem séries estacionárias autocorrelacionadas.
- Propósito. "Retreina ou mantém" e "ao lado de um detector" aparecem como uso pretendido, não testado. O "24 de 43" diz que conta os eventos depois do aquecimento (24/43, 224 falsos, 1,96 por mil: confere).
- CUSUM 439/453. 258+181 de 266+187, duas variantes: confere.
- M5. Os minutos [718, 740, 815, 681, 699] dão 11 a 14 h, e o relógio conta a partir de "off the air".
- Veredito e M2. A decomposição 3/2/5 e o empate de M2 estão nas telas.
- Paridade EN/PT. Não achei divergência de número.

## 2. Problemas novos

### Substância

1. O S3 continua contando como "vitória" no 3/2/5. O protocolo marca S3 como WON, mas na única metade em que há comparação direta (as 210 mudanças de entrada) o ADWIN faz 210/210 e o Sismo 209/210. A vitória vem só das 270 relações, onde os concorrentes não podem pontuar. A legenda já diz isso, mas o veredito "3 vitórias" ainda soma S3. Sugiro "2 vitórias + 1 por capacidade" (S3), ou uma nota no veredito.
2. A coluna "quando começou" não aplica o teto de falso alarme que a tabela aplica nas outras.
   - O 96,9% do CUSUM junta `cusum/error h=5,k=0.5` de S1 (266 detectados) e `cusum/field h=5` de S2 (187).
   - A primeira configuração tem nulo em 370 de 370 séries com alerta (`rows.json`, linha S7). Pelo critério da própria tabela, ela levaria †.
   - Na tela, o 96,9% aparece sem marca, ao lado de "F1 de alerta 0,206†" do mesmo CUSUM. A ressalva 8 menciona as variantes, mas não que uma delas é inelegível.
   - Sugiro † nessa célula ou nota "inclui configuração acima do teto". Alternativa: mostrar só S2, onde Sismo faz 155/210 (73,8%) contra 96,8% do CUSUM.
3. A métrica de várias linhas não está dita e muda de natureza. S3, S5, M1, M2, P4o e as linhas L4 são sensibilidade (`metric: sensitivity` no `rows.json`), não F1. Na tela, tudo aparece como número solto e a legenda só diz "maior é melhor".
   - O caso mais grave é P4L4: o 0,071 é só 9/127 de recall. O F1 dessa linha é 0,0068, com 2.525 falsos e nulo de 5,06 por mil.
   - O Sismo aparece nela sem †, embora na linha P4 acima (mesma base) o nulo dele reprove. A ressalva 13 explica isso (o nulo do detector não se aplica às linhas de limite), mas a tela não.
   - Sugiro rotular a métrica por linha e dizer na legenda por que o Sismo não leva † nas linhas L4.

### Menores

4. O gerador das telas não está no pacote. O rodapé diz "um comando reproduz cada número", mas nada em `reproduce.sh` nem no README gera as telas. Os agregados (71,2%, 96,9%, 97,8%, as colunas de recursos, o † e o ‡) não são recalculáveis pelo comando. O erro do † de S5 (ressalva 25) veio justamente desse gerador. Publique-o junto, ou troque o rodapé por "reproduz as linhas; as telas são derivadas delas".
5. O S7 conta 370 "séries sem mudança". Pela 3ª avaliação, 190 delas são cópias embaralhadas (190/190 no CTM), e isso explica a dependência entre as séries. Não confirmei a composição. Confira antes de publicar e, se bater, diga na legenda de S7 quanto é nulo genuíno e quanto é embaralhado.
6. O subtítulo "Every column measured" contradiz o ‡. A tela de recursos diz isso no subtítulo, mas as células ‡ dizem "não é medida". Sugiro "toda coluna rodada".
7. O S5 é empate com mais do que "os métodos por campo". Por `rows.json`, CJSD e isolation forest também fazem 1,000. Além disso, o "sem alerta" é trivial para método que nunca alerta. A tela e a ressalva falam só em "métodos por campo". Troque por "empata com 9 métodos, vários sem alerta".
8. O "XOR" na coluna "não passa" do placar é uma linha de limite que não decide. L1, L2 e L4 também ficaram "limite não confirmado" e não aparecem. A seleção é conservadora, mas assimétrica. Uma linha "limites declarados" resolveria.
9. O hash na legenda. A ressalva 21 já diz que ele prova conteúdo, não data. O rodapé das telas ("congelado antes", ed41901c) ainda lê como prova de cronologia.

## 3. Ressalvas de `RESSALVAS.md`

Não achei nenhuma ressalva da avaliação 1, 2 ou 3 faltando ou mal resolvida. Pontos de redação:

- Os itens 2 e 3 do bloco acima deveriam entrar como ressalvas novas (31 em diante).
- A ressalva 12, "o único que responde a tudo aqui", está ok. Mesmo assim, o CUSUM ganhar a coluna "quando" faz o título "responde a tudo" valer só como cobertura, não como qualidade.
- A ressalva 15 (critério de empate) diz "repositório pendente". Diga também que "tied" no M2 vem de SE = 0, o caso degenerado.

Nenhum desses pontos muda o veredito nem o 10/18.
