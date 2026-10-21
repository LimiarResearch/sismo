# Painéis do benchmark do Sismo (oitava versão, 18/10/2026)

Este pacote vai para uma oitava avaliação independente. As sete anteriores estão em `avaliacoes_anteriores/` (com os scripts da quinta e da sexta), e tudo o que elas apontaram está em `RESSALVAS.md`, item por item, com a origem e a situação de cada um.

O veredito está nas linhas: não aprovado, 10 das 18 linhas que decidem (2 vitórias, 1 por capacidade, 2 empates, 5 contra um nulo ou um teto).

## O que tem aqui

`prints/`: as oito telas, quatro em inglês e quatro em português.

| arquivo | tela |
|---|---|
| 01_Capabilities-en, 05_Recursos-pt | o que cada método devolve |
| 02_Purpose-en, 06_Proposito-pt | por que não passa nas bases públicas e para que serve |
| 03_Scorecard-en, 07_Placar-pt | onde passa, onde não passa e os limites declarados |
| 04_Results-en, 08_Resultados-pt | a tabela completa: as 26 linhas contra os 15 concorrentes |

`gerador/`: como as telas são feitas e conferidas.

| arquivo | o que faz |
|---|---|
| `numeros_das_telas.py` | calcula as células e os fatos das telas a partir do `rows.json` e, com as pastas de `publication.zip` e `lives.zip`, os números que não estão nele (séries, nulos de S7, S3 por tipo, registros e alvos do M3, respostas do S4a, incidentes independentes do M2); para se o melhor concorrente elegível de alguma linha não for o `best_value` do protocolo, se não achar saídas ou vidas, ou se o universo não fechar com as linhas. Saída: `numeros.json` |
| `telas.py` e `moldes/` | geram as oito telas. Todo número visível entra por uma chave ou por uma função que diz de onde ele vem (rows.json, numeros.json, metrics/rows.py, protocol/seeds.json, rótulos das linhas). O gerador para se sobrar no texto visível algum dígito sem fonte que não seja identificador (S1, P4L4, F1, sha256). Constantes fora dos dados: a data da revisão que achou os defeitos de adaptador e os nomes dos métodos |
| `auditoria.py` | recalcula o `numeros.json`, roda o gerador e exige que cada tela publicada (`telas_html/`) seja igual, byte a byte, à gerada; depois refaz as conferências independentes (cada célula, †, ‡, caixa de vencedor e veredito contra o `rows.json`, frases com números nos dois idiomas, paridade de números e de 11 termos técnicos entre idiomas, sha256 do logo). Sem as pastas `publication` e `lives` ela reporta problema, a menos que se passe `--parcial` de propósito. Saída: `auditoria_saida.txt`, 0 problemas |
| `teste_mutacao.py` | 32 erros plantados, um por vez: os 11 da 5ª avaliação, as 10 mutações dirigidas da 6ª, os casos da 7ª (universo adulterado com a auditoria completa, tradução trocada, logo trocado, auditoria sem pastas e sem `--parcial`) e outros, mais um `numeros.json` adulterado, um texto sem número trocado e um número escrito à mão num molde. Antes, exige 0 problemas sem mutação. Só conta "pegou" com código 1 e "problemas: N" com N > 0. Saída: 32 de 32 |
| `teste_exaustivo.py` | os testes exaustivos da 6ª avaliação: cada um dos 1.062 números do texto mudado num idioma, e os 530 números mudados nos dois idiomas ao mesmo tempo. Saída: 0 sobreviventes nos dois |
| `render_prints.mjs`, `confere_prints.py` | renderizam o HTML de novo com Chromium e comparam pixel a pixel com `prints/`; qualquer pixel diferente é problema (o render é determinístico). Saída: 0 pixel diferente nas 8 telas |

```
# na raiz do repositório, com publication.zip e lives.zip descompactados
python paineis/gerador/numeros_das_telas.py . numeros.json <pasta publication> <pasta lives>
python paineis/gerador/auditoria.py . numeros.json paineis/gerador/telas_html <pasta publication> <pasta lives>
python paineis/gerador/teste_mutacao.py . numeros.json paineis/gerador/telas_html <pasta publication> <pasta lives>
python paineis/gerador/teste_exaustivo.py . numeros.json paineis/gerador/telas_html
node paineis/gerador/render_prints.mjs paineis/gerador/telas_html <pasta nova>    # precisa de Playwright
python paineis/gerador/confere_prints.py paineis/prints <pasta nova>
```

Com `--parcial` no lugar das pastas, a auditoria roda em menos de um segundo e usa o universo do `numeros.json` sem recalcular; é o modo que os testes de mutação usam para os erros no HTML, e ela diz "AUDITORIA PARCIAL" na saída.

## Validação do detector

A pré-validação do detector foi feita sobre um repositório interno e não é publicada aqui. O que ela concluiu sobre o benchmark está no README: a tabela vale para o detector publicado em `detector/`, e qualquer outra versão precisa ser medida de novo sob o mesmo protocolo. A validação independente continua necessária.

## O que mudou desde a sétima avaliação

- Os três caminhos que passavam pela auditoria foram fechados:
  - PNG: `confere_prints.py` exige 0 pixel de diferença;
  - universo: sem as pastas, a auditoria reporta problema, salvo `--parcial` pedido de propósito, e o teste de mutação tem o caso do universo adulterado com a auditoria completa;
  - caminho errado: `numeros_das_telas.py` para se não achar saídas ou vidas e confere o universo contra as linhas do `rows.json`.
- As chaves que acertavam por coincidência agora têm fonte própria: a base do S4a, cada 0, o "todas sobem" e os nomes de métrica dos rótulos.
- Nessa conta apareceu uma imprecisão nas telas: das 209 respostas do S4a, 179 são de campos numéricos (que sobem) e 30 de categóricos. O texto agora diz que a resposta certa é fixa nos 209.
- "costume" virou "aquecimento". A auditoria passou a conferir termos técnicos entre os idiomas e o logo.
- Telas:
  - M2 diz "no máximo 4 independentes";
  - a legenda do "quando começou" dá também as taxas sobre as 480 mudanças;
  - a tabela diz "sintéticas que decidem".
- `RESSALVAS.md`: itens 2, 5, 8 e 34 atualizados; entraram os itens 49 a 54.

## O que ainda não mudou

O repositório e o cartão do Hugging Face deste pacote são a versão anterior às avaliações, inclusive "before any run" e "ran once" no README e no cartão. As mudanças de documentação entram de uma vez no fim desta revisão, sem alterar os arquivos congelados nem a rodada arquivada.

Atualização de 21/10/2026: as mudanças de documentação entraram no README, na seção "Known limitations and caveats", com o número de cada item desta lista; a versão original do repositório é o commit `db2b946` (14/10/2026), no histórico. Os arquivos congelados e a rodada arquivada não mudaram.

Atualização de 21/10/2026, depois de uma pesquisa sobre trabalhos anteriores: três telas em cada idioma mudaram só no texto, sem nenhum número novo.
- Recursos: o título "O único aqui que devolve tudo" virou "Tudo num aviso só", com "Nenhuma das peças é nova"; a legenda diz que um CUSUM bilateral pode dar direção e tamanho, não calculados nesta bancada, e que o CJSD (Oda) e o WATCH (Prinster et al.) são os parentes publicados mais próximos da separação entre alerta e log.
- Propósito: "Nenhuma dessas peças é nova; ele as junta num aviso só", e a autocorrelação passa a ser "no mínimo tão provável" quanto as mudanças sem rótulo.
- Resultados: a legenda diz de quem são o CJSD e o WATCH.
A auditoria, os testes de mutação (32 de 32), o exaustivo (0 sobreviventes) e a conferência dos prints (0 pixel) foram rodados de novo.

As correções de código ficam para a v2:
- adaptadores do CJSD e do WATCH;
- associação exclusiva no M3;
- quedas em S4a;
- nulos autocorrelacionados;
- configuração dos concorrentes fixada antes da rodada.

## O que pedimos à avaliação

1. Conferir se as correções da sétima avaliação estão certas.
2. Tentar fazer passar pela auditoria uma tela com um erro, de qualquer tipo. Com o desenho novo, o que sobra para conferir é se cada chave do gerador aponta para o valor certo (a função `valores()` em `telas.py` e as regras de `numeros_das_telas.py`).
3. Conferir se alguma ressalva de `RESSALVAS.md` ficou de fora ou mal resolvida, e apontar qualquer problema novo.
4. Se quiser ir além das telas: medir o detector publicado em `detector/` por conta própria, tratando as conclusões do README como hipóteses a derrubar.
