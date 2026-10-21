# Avaliação independente (6ª) do benchmark Sismo, telas e gerador

Resumo: as correções da 5ª avaliação estão certas. O gerador reproduz tudo. Mas a auditoria ainda deixa passar vários tipos de número, e há dois pontos novos nas ressalvas, um deles sobre o M3.

O que fiz:

- Li o LEIAME, as RESSALVAS e o parecer 5.
- Confirmei que a pasta paineis/ é idêntica nos dois zips.
- Rodei numeros_das_telas.py com publication.zip e lives.zip, depois a auditoria e o teste de mutação.
- Escrevi mutações próprias (uma exaustiva por número, uma exaustiva em pares EN/PT e uma dirigida).

O que não fiz: não recalculei o rows.json do zero (python -m metrics.rows), não reexecutei detector nem concorrentes e não abri os PNG. A auditoria só lê o HTML.

## 1. As correções da 5ª avaliação

Estão certas. O gerador passa a conferência do best_value nas 16 linhas com concorrente, e a auditoria dá 0 problemas. Recontei nas saídas:

- S3: relações 270 (Sismo 269, ADWIN 0), entradas 210 (Sismo 209, ADWIN 210).
- S7: 180 nulas e 190 embaralhadas. Total de 2.047 séries.
- M3: 10 acertos, 6 registros por vida, 3 por rota e minuto.
- Nulo combinado em 2,48, 0,63 e 0,54 (P4, P5 e P6). O bloco "Por que nenhum veredito depende de 1, 2 ou 3" está correto.
- Veredito: 10 de 18, com 2 vitórias, 1 por capacidade, 2 empates e 5 contra nulo ou teto. O texto do M4 no placar também está certo.
- Os melhores concorrentes citados (HDDM_W em P1, teste por campo em P5, matrix profile em M1) são sem ‡, como diz o texto.
- O hash ed41901c… bate com protocol/seeds.json.

## 2. O gerador e o teste de mutação

- numeros.json sai igual em conteúdo. Em bytes difere só por CRLF contra LF, porque os arquivos são escritos em modo texto no Windows.
- A auditoria dá 0 problemas, com a mesma contagem do LEIAME: 116 números de texto.
- O teste de mutação só fecha 22 de 22 com -X utf8 no Windows. Sem isso, o filho imprime em cp1252, o pai tenta ler como UTF-8 e dá UnicodeDecodeError. O item 43 diz que o problema do encoding foi resolvido, mas só vale para open().
- O critério do teste confunde falha com detecção. Ele conta "pegou" sempre que o código de saída é diferente de 0. Na minha primeira rodada, sem o numeros.json, a auditoria quebrou e o teste mesmo assim imprimiu "22 de 22". Deveria exigir problemas: N com N maior que 0 na saída.

## 3. O que a auditoria ainda deixa passar

Mutei cada um dos 1.048 números do texto das telas, um por vez, em cada arquivo. Os que sobrevivem, fora a falha de critério acima, são poucos, porque a paridade EN/PT pega a troca em um idioma só. Depois mutei os mesmos números ao mesmo tempo nos dois idiomas, que é o caso que a paridade não pega: 88 de 523 pares passaram. Confirmei os tipos abaixo com mutações dirigidas, todas com "0 problemas":

| tipo de número | exemplo que passou |
|---|---|
| Duas colunas da tela de recursos nunca são lidas (a auditoria só olha as colunas 0, 1, 4, 5 e 6) | "direção e tamanho" 100% → 90%; "novo normal" 97,8% → 87,8% |
| Célula do Sismo nas linhas sem concorrente | S7 "0 · 6" → "5 · 6"; M4 "2 of 3" → "3 of 3" |
| Parâmetros nos rótulos de linha e títulos | "60 min" → "90 min" (M1); "up to 20"; "0.25 sd"; "500 items"; "< 10 items"; "38 fields"; "All 26 rows" |
| Hash do rodapé | ed41901c → aaaa1111 nas 8 telas (a paridade remove sha256 \w+) |
| Cabeçalho das colunas (não é número, mas é do mesmo tipo de lacuna) | trocar ADWIN e KSWIN no cabeçalho: as células continuam "certas" por posição |
| Folga de arredondamento nas células | a tolerância de 0,00051 aceita 0,405 onde o valor real é 0,40449 (L1/KSWIN) e 0,399 onde é 0,3985 (P4o/HDDM_A) |

Correções simples:

- Comparar f"{v:.3f}" com o texto da célula.
- Ler o cabeçalho das colunas.
- Conferir as colunas de recursos que faltam.
- Conferir as células do Sismo em S7 e M4.
- Derivar os parâmetros dos rótulos do texto da linha no rows.json e do rows.py.
- Ler o hash de protocol/seeds.json.

O LEIAME fala em "cada célula e os números citados nos textos". Isso vale para as tabelas, não para todos os números das telas.

## 4. Ressalvas: mal resolvidas e novas

- M3, o minuto igual em vidas de sementes diferentes não indica dados compartilhados. O item 3 e o parecer 5 sugerem isso, mas as 525 ocorrências de became_new_normal caem todas em minutos múltiplos de 100 (minuto + 1). Dois processos independentes coincidem em 38.800 por causa dessa grade. Já o 18.600 repetido nas variantes da vida de semente 746892 é dependência real (mesma semente). Então "3 registros por rota e minuto" está inflado: o certo é 4 registros nas três vidas normais, como o próprio item já diz. Sugiro explicar a grade no item 3.
- O denominador de M3 não aparece. Os 15 alvos são 8 nas três vidas normais (8 acertos), 4 nas variantes (2 acertos) e 3 na vida embaralhada (0 acertos). A frase "os acertos nas três vidas independentes são 8" não diz que isso é 8 de 8. Pelo nome, a vida embaralhada é um nulo onde esses 3 alvos não podem ser acertados. Não li read_truth para confirmar. Vale uma linha dizendo o que entra nos 15.
- O item 34 (e a linha do LEIAME sobre a auditoria) deveria registrar a lista da seção 3 e a falha de critério do teste de mutação (seção 2).
- Cobertura: as ressalvas das cinco avaliações anteriores têm item correspondente. Os itens 41 a 46 batem com o que o parecer 5 pediu. Não achei nada que mude o 10/18.

Os scripts estão em avaliacao_6_scripts/: mutacoes_dirigidas.py, mutacao_exaustiva_um_idioma.py e mutacao_exaustiva_pares_en_pt.py. Rodei em Python 3.13 no Windows, com numpy em um venv temporário.
