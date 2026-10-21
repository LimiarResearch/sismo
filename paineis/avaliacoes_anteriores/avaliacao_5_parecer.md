# Avaliação independente (5ª) do benchmark Sismo, telas e gerador

Material: `github_sismo_v5.zip` e `huggingface_sismo-benchmark-runs_v5.zip`. A pasta `paineis/` é idêntica nos dois (`diff -r` sem diferença). Li LEIAME, RESSALVAS, os quatro pareceres, `gerador/`, `metrics/rows.py`, o trecho de `competitors/methods.py` sobre CJSD e WATCH, e as telas.

**O que fiz.** Rodei `numeros_das_telas.py` e `auditoria.py` (reproduzem: `numeros.json` igual, 0 problemas). Recalculei `rows.json` do zero com `python -m metrics.rows` sobre `publication.zip` e `lives.zip`: igual ao publicado (diferenças abaixo de 1e-9). Recontei nas 2.047 saídas o que não está em `rows.json`. Escrevi testes próprios para a auditoria e para as regras do gerador (em `avaliacao_5_scripts/`).

**O que não fiz.** Não reexecutei detector nem concorrentes. Vi as imagens 01 a 05 e 07; não vi 06 e 08. A auditoria só lê o HTML, então não confiro que cada PNG é o render desse HTML.

## Resumo

1. As correções da 4ª avaliação estão certas nas telas.
2. As regras do gerador batem com `metrics/rows.py` nos pontos que testei. A auditoria, porém, deixa de fora vários tipos de número: de 11 erros plantados nos HTML, 9 passaram com "0 problemas".
3. Nenhuma ressalva das quatro avaliações ficou de fora. Uma está mal resolvida (erro herdado da 3ª avaliação) e achei quatro problemas pequenos. Nenhum muda o 10/18.

## 1. As correções da 4ª avaliação

Conferi contra `rows.json` e contra as saídas.

- **S3 por capacidade.** Nas saídas: relações 270, Sismo 269 e ADWIN 0; entradas 210, Sismo 209 e ADWIN 210. O 43,75% é 210/480.
- **Veredito 2 + 1 + 2 + 5.** Passam S1 e S2 (vitórias), S3 (capacidade), S5 e M2 (empates) e S4a, S4b, S4c, S7 e M3 (nulo ou teto): 10. Decidem 18. Reprovam P1, P4, P4o, P5, P6, M1, M4 e M5: 8.
- **CUSUM 78,0%.** São 209/268, com as configurações da tabela completa.
- **P4L4.** São 9/127, com 2.525 falsos e F1 de 0,0068.
- **S7.** As 2.047 saídas têm 180 séries nulas (6 famílias × 30) e 190 cópias embaralhadas. S7 usa 370.
- **S5.** São 9 métodos com 1,000.
- **Placar.** O nulo no treino vai de 2,20 a 5,15 por mil. O combinado vai de 0,54 (MSL) a 2,48 (SMD), e SMAP dá 0,63. O teto é 0,1.
- **Rodapés.** Dizem agora que o hash prova conteúdo, não data.
- **Outros números.** 2.047 séries confere. "6 registros distintos" confere se contados por vida (reproduzi: 10 acertos, 6 registros). Ver 3.2.

Pontos de leitura nas telas:

- **M4 no placar.** "2 de 3 vidas · uma vez na vida sem deriva" não diz que a linha falha por dois motivos. Uma das três vidas normais tem 0, e a vida sem deriva dispara 1 vez quando deveria dar 0 (`rows.json`: normal `[2, 0, 1]`, sem deriva `[1]`). Sugestão: "2 de 3 vidas normais; a vida sem deriva também disparou (devia ser 0)".

## 2. Gerador e auditoria

### 2.1 As regras batem com `metrics/rows.py`?

Batem. Verifiquei na leitura:

- tetos 2%, 5%, 0,1 por mil e 0,3;
- S2 pelo log; S3 pelos dois; S5 e L1 a L3 pelo alerta;
- bases públicas pelo nulo combinado, com P4o e P4L4 usando o de P4;
- configuração sem nulo medido fica elegível;
- nulo do detector não se aplica às linhas de limite nem a P1c;
- famílias que nomeiam campo em S3 e P4o.

**Teste novo.** Para as 16 linhas com concorrente, o melhor valor elegível que o gerador calcula é exatamente o `best_value` que o `rows.py` gravou (`confere_melhor_concorrente.py`). O gerador não faz essa conferência e deveria. Isso valida a elegibilidade dos candidatos ao máximo; não prova o † de cada célula não vencedora.

**Os ‡ batem com o código.**

- O CJSD só fica sem aviso quando `y is None`, e as 27 famílias sintéticas têm resposta. Por isso os 8 ‡ são P1, P1c, P4, P4L4, P5, P6, M1 e M2.
- O WATCH ponderado só roda com resposta (`methods.py:270`). Por isso os 6 ‡ são S1, S2, S5 e L1 a L3.

**Diferenças e riscos (nenhum muda um número hoje):**

1. **Listas escritas à mão.** `DETECTOR_FORA`, `DEFEITO` e `COM_CONCORRENTE` estão no código, e o †/‡ do detector em S2 (alertas indevidos), M1 e M2 não é calculado. Hoje está certo: nulo do detector 0,0 em P1, M1 e M2; S7 com 0/370 e 6/370; alertas indevidos 0/30 em todas as famílias de S2. Mas nada confere isso.
2. **Regra de exibição que não é do `rows.py`.** O `rows.py` pega um melhor global por linha. A célula do gerador escolhe a melhor configuração por família e, se a melhor elegível vale 0 e outra passa de 0, mostra essa com †. Está no docstring ("que pontua") e na legenda, mas não é regra do protocolo.
3. **Arredondamento.** A elegibilidade lê nulos arredondados (3 casas em M, 4 em P). Nenhuma célula cai dentro do erro de arredondamento (os mais próximos do teto: M 0,273 contra 0,3; P 0,0971 e 0,1052 contra 0,1, a mais de 0,002).
4. **Fatos do texto.** "Empata com 9 métodos" conta qualquer configuração com 1,000, sem olhar elegibilidade (coincide hoje). "2,2 a 5,1" e "0,5 a 2,5" assumem que P6 é o mínimo e P4 o máximo em vez de calcular (vale hoje, com SMAP no meio).
5. **Texto fixo em `sintese`.** A frase "209/210 e 269/270" é texto escrito, não cálculo. Está correta (recontei).
6. **Windows.** `open()` sem `encoding` quebra com `UnicodeDecodeError` em Python no Windows (cp1252). O erro aparece em `auditoria.py:23`. É preciso `python -X utf8`. Note que `-I` ignora `PYTHONUTF8`. Sugestão: `encoding="utf-8"` em todos os `open`.
7. **Circularidade.** A auditoria confere o HTML contra um `numeros.json` calculado com as mesmas regras. Ela prova a renderização, não a regra. O teste do 2.1 cobre essa lacuna.

### 2.2 A auditoria deixa algum tipo de número de fora? Sim

Teste de mutação (`teste_mutacao_auditoria.py`): troquei um número por vez nos HTML, nos dois idiomas quando o número aparece nos dois, e rodei a auditoria.

| erro plantado | pegou? |
|---|---|
| "6 registros distintos" → 7 | não |
| nulo de S4b 0,240 → 0,340 (nota da linha) | não |
| F1 de P4L4 na legenda 0,007 → 0,017 | não |
| "2 empates, 5 contra nulo" → "3 empates, 4" | não |
| "2 vitórias, 1 por capacidade" → "3 vitórias, 0" (tabela completa) | não |
| 180 nulas e 190 embaralhadas → 170 e 200 | não |
| 2.047 séries → 2.147 | não |
| teto público 0,1 → 0,2 (legenda) | não |
| M4 "2 de 3" → "3 de 3" | não |
| "24 de 43" mudado só em EN | sim (texto ausente em EN) |
| 71,2% → 72,2% na tela de recursos | sim |

O que fica de fora, por tipo:

- **Constantes e tetos das legendas.** Nada compara 0,1, 0,3, 2% e 5% com `rows.py`.
- **Notas das linhas só do Sismo.** Para S4a, S4b, S4c, M3 e M5 só o valor do Sismo é conferido. Ficam sem conferência `null 0.240`, `n 179`, `n 180`, `n 209`, `n 7`, `6 distinct records` e o texto de M4.
- **Decomposição do veredito.** Só "10 of the 18" é conferido, não "2 vitórias, 1 por capacidade, 2 empates, 5".
- **Números que não estão em `rows.json`:** 2.047 séries, 180/190 do S7, 15 concorrentes, 6 registros, 209/210 e 269/270. Recontei todos nas saídas e estão certos; a auditoria não os confere.
- **O português.** O PT só passa pela paridade, que compara o multiconjunto de números. Um número alterado igual nas duas línguas passa.
- **Os PNG.** Não são conferidos contra o HTML.

Por isso o texto do LEIAME ("confere cada célula … os números citados nos textos") promete mais do que a auditoria faz: 32 números do texto, de dezenas.

## 3. Ressalvas e problemas novos

### 3.1 Cobertura

Cruzei os quatro pareceres com a lista. Não achei ponto de nenhuma avaliação sem item correspondente em `RESSALVAS.md`.

### 3.2 Mal resolvido ou novo

1. **O bloco "Por que nenhum veredito depende de 1, 2 ou 3" repete um erro da 3ª avaliação.** Diz que P4, P4o e P6 reprovam pelo nulo do próprio Sismo "(5,15, 3,11 e 2,20 por 1.000 itens contra o teto 0,1)". Esses três números são o nulo só do treino de SMD, SMAP e MSL. O 3,11 é de SMAP (P5), não de P4o. Comparar o treino sozinho com o teto é o erro que o item 40 corrigiu no placar. Os valores do nulo combinado são P4/P4o 2,48, P5 0,63 e P6 0,54. As conclusões não mudam (todos passam do teto).
2. **M3 "6 registros distintos" é por vida.** Reproduzi o cálculo. Os 10 acertos caem em 6 pares (vida, campo, minuto). Contando (rota, minuto), são 3. O mesmo minuto repete entre vidas: notas fiscais em 18.600 aparece em 3 vidas (`sem_defeito_s7`, `normal_s746892`, `sem_deriva_s74`), notas fiscais em 38.800 em 2 (`normal_s155069`, `normal_s479019`), e catálogo em 26.700 em 1 (`normal_s479019`). Um mesmo minuto em vidas de semente diferente indica que esses processos compartilham dados, mas isso eu não verifiquei. O item 22 trata a dependência em geral; este número específico merece uma linha.
3. **O item 34 e o LEIAME exageram o alcance do gerador e da auditoria** ("todos os números das telas", "confere cada célula e os números citados nos textos"). Ver 2.2. Sugestão: "todas as células das tabelas e 32 números do texto".
4. **Seleção da melhor configuração com os dados da aprovação.** Cada célula de concorrente mostra a melhor de duas configurações, escolhida depois de ver o resultado. O Sismo tem uma só. A avaliação 2 apontou isso no ranking, que saiu; o mesmo vale para a tabela. É conservador para as vitórias do Sismo, mas conta nas linhas perdidas ou empatadas (M1 perde por 0,300 contra 0,284). Vale uma linha em RESSALVAS.
5. **A reprodução da 1ª avaliação** rodou em Windows com Python 3.13; o ambiente original era Linux com Python 3.11.17. A minha também, com diferença abaixo de 1e-9. Opcional.

## 4. Sugestões antes do envio

- Corrigir o bloco de 3.2.1, acrescentar 3.2.2 e 3.2.4 a RESSALVAS, e reescrever o item 34 e o LEIAME conforme 3.2.3.
- No gerador: `encoding="utf-8"`, o teste do `best_value` do 2.1 e listas derivadas dos dados quando der. Na auditoria: constantes de `rows.py`, notas das linhas só do Sismo, decomposição do veredito e os números do universo que dependem de `publication.zip`.
- Reescrever a célula de M4 no placar (seção 1).
- Já pendentes e inalterados: README do GitHub e cartão do Hugging Face ("before any run", "ran once").

Nenhum desses pontos muda o veredito nem o 10/18.
