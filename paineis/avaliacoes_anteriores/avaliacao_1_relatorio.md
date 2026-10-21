**Verificação independente do Sismo — 18/10/2026**

**Parecer:** os principais números do benchmark são reproduzíveis. A conclusão geral continua sendo **não aprovado: 10 de 18 critérios passaram**. Há, porém, um erro concreto na matriz usada pelo ranking e limitações importantes nas interpretações das telas. O desempenho sintético favorável não estabelece, sozinho, confiabilidade geral em séries operacionais.

Material examinado: `github_sismo.zip`, `huggingface_sismo-benchmark-runs.zip`, o `ranking.zip` enviado em seguida e as três capturas de tela. Os originais foram preservados. Esta é uma análise dos artefatos e de testes executados nesta máquina; não é certificação da história de desenvolvimento ou da operação de uma empresa real.

**O que foi efetivamente conferido**

- Os 66 arquivos do manifesto de publicação correspondem aos SHA-256 declarados. As 33 sementes foram recalculadas a partir do manifesto original e conferem.
- As 2.047 saídas da aprovação e da publicação coincidem após a tradução dos nomes: avisos, relatos e eventos; os tempos de máquina são excluídos da comparação. O manifesto de avisos da publicação também confere.
- As 26 linhas foram recalculadas a partir das saídas e das vidas da empresa simulada. Contagens, métricas decisórias e veredictos conferem. Há 82 diferenças de arredondamento em medidas auxiliares, de no máximo 7,11 × 10⁻¹⁵, sem efeito na tabela apresentada.
- Uma implementação própria de contagem verificou eventos detectados, falsos avisos e F1 de todos os métodos presentes em S1, S2 e nas quatro bases públicas, sem divergências materiais.
- O detector foi reexecutado em **34 séries distintas**: as 27 famílias sintéticas com a primeira semente aprovada, uma série de cada base pública e três processos de uma vida simulada. Avisos, relatos e trajetórias coincidiram exatamente. Não foram reexecutados todos os concorrentes nas 2.047 saídas.
- Os dados da amostra pública vieram dos commits fixados, com hashes conferidos. Os escores oficiais NAB foram recalculados pelo código oficial fixado: **44 escores conferidos**, com tolerância numérica de 10⁻⁸. Sismo: **14,27** nas 36 séries de aprovação e **16,27** nas 58 séries com configurações padrão.

As reexecuções do detector usaram Windows, Python 3.13.3, NumPy 2.4.6, SciPy 1.17.1 e river 0.26.1. O NAB foi avaliado em ambiente separado, Python 3.11.9, com as dependências fixadas em requirements-nab.txt. O ambiente original era Linux/Python 3.11.17; a reprodução exata da amostra é evidência favorável de portabilidade, sem equivaler à reprodução integral do experimento.

**1. Ranking: primeiro lugar preservado, tabela dos concorrentes precisa de correção**

Executar `rank_final.py` sobre a matriz fornecida reproduz exatamente `ranking_saida.json` e os números das telas: Sismo 3,3; DDM 3,9; ADWIN 4,2 etc. O cálculo do script é consistente com essa entrada.

A entrada, contudo, contém **25 classificações de elegibilidade incompatíveis com os próprios controles do benchmark**: 10 em S1, oito em S2, cinco em S3 e duas em S5. Os valores numéricos de 228 células examinadas conferem; o erro está em aceitar configurações que ultrapassam o teto. Exemplo: Page-Hinkley em S1 tem aviso em 46/370 controles, ou 12,43%, acima do teto de 2%, mas aparece como elegível na matriz. WATCH em S1 tem 360/370, ou 97,30%, e também entra como elegível.

Corrigi somente esses rótulos, mantive as configurações escolhidas pela matriz e executei o mesmo script, com as mesmas regras de empate e ausência de resultado. **Sismo permanece em 1º, média 3,3, cinco primeiros lugares em dez tarefas.** Os demais postos mudam:

| Posição | Método | Média corrigida | Tarefas |
|---|---|---|---|
| 1 | O detector | 3.3 | 10 |
| 2 | HDDM_A | 3.9 | 10 |
| 3 | ADWIN | 4.0 | 10 |
| 4 | DDM | 4.0 | 10 |
| 5 | HDDM_W | 4.2 | 10 |
| 6 | Isolation forest | 4.78 | 9 |
| 7 | CJSD | 4.89 | 9 |
| 8 | Teste por campo | 5.2 | 10 |
| 9 | KSWIN | 5.3 | 10 |
| 10 | CUSUM | 5.4 | 10 |
| 11 | Page-Hinkley | 5.6 | 10 |
| 12 | EWMA | 5.9 | 10 |
| 13 | Matrix profile | 6.0 | 10 |
| 14 | WATCH | 6.78 | 9 |
| — | HTM | 7.0 | 3 |
| — | CTM | 9.33 | 3 |

Essa correção não refaz a escolha da melhor configuração elegível de cada família; é uma reparação mínima da matriz recebida. O ranking também compara médias com denominadores diferentes: três métodos têm nove tarefas, os demais classificados têm dez. Métodos reprovados pelo teto podem receber posição 2 quando apenas um método é elegível. Portanto, “1º entre 14” deve permanecer vinculado a **esse agregado e a essas regras**, sem sugerir aprovação geral ou superioridade em todas as bases. O ranking não consta como critério decisório do protocolo original examinado.

**2. “209 de 209 na direção”: número correto, evidência limitada**

O código de S4a verifica `direction == "up"`; para categorias, verifica aumento da categoria zero. Todas as alternativas esperadas nessa amostra apontam para aumento. Assim, uma resposta constante “subiu” — ou “a participação de zero aumentou” — também alcança 209/209. O teste contra uma moeda de 50% é insuficiente para demonstrar capacidade de distinguir subidas de quedas.

Os 179/179 de tamanho também conferem, mas são condicionais aos relatos selecionados, no campo verdadeiro, e são medidos **500 itens depois do aviso**. Não são 179 estimativas feitas no instante inicial do alerta, nem uma avaliação de todos os campos e magnitudes possíveis. Para sustentar uma afirmação geral, incluir quedas, sinais balanceados, amplitudes e ruídos variados, além de mostrar cobertura e erros antes dos 500 itens.

O resultado “onde” também é específico: 478/480 eventos com aviso e todos os campos acusados pertencentes à verdade. A regra aceita um subconjunto correto dos campos verdadeiros; não exige recuperar todos os campos que mudaram.

**3. Baixo resultado nas bases públicas é real**

| Base | F1 de eventos | Eventos detectados | Avisos fora das janelas | Precisão de eventos |
|---|---|---|---|---|
| NAB | 0.165 | 24/43 | 224 | 9.7% |
| SMD | 0.063 | 80/133 | 2311 | 3.3% |
| SMAP | 0.091 | 32/44 | 627 | 4.9% |
| MSL | 0.222 | 11/18 | 70 | 13.6% |

A precisão acima usa a definição do protocolo: eventos detectados / (eventos detectados + avisos fora das janelas). Vários avisos dentro da mesma janela não são todos contados como acertos separados. “Fora da janela” significa falso aviso segundo a rotulagem do benchmark; não prova, por si, que inexiste alguma mudança física naquele instante.

No trecho de treino tratado como controle, as taxas são 5,146 por mil em SMD, 3,111 em SMAP e 2,200 em MSL, contra teto 0,1. O zero nas cópias embaralhadas também confere. A explicação das telas de que os avisos excedentes são mudanças reais não rotuladas é **uma hipótese**, não uma conclusão demonstrada por esses números. É necessária inspeção/rotulagem independente dos avisos, incluindo sazonalidade e dependência temporal.

As janelas públicas toleram aviso até depois do fim do evento, por até sua duração ou dez itens. Como análise de sensibilidade, mantendo os demais critérios e restringindo os avisos à duração marcada, o F1 do Sismo cai de 0,063 para 0,045 em SMD, de 0,091 para 0,083 em SMAP e de 0,222 para 0,157 em MSL. Isso não invalida as janelas declaradas; limita a interpretação de detecção “a tempo”.

**4. Teste novo: séries estacionárias com autocorrelação**

Executei 40 séries novas, cada uma com 20.000 itens, um campo, aquecimento de 2.000 e o detector padrão. São processos gaussianos AR(1), inicializados em sua distribuição estacionária, sempre com média zero e variância um. Não foi introduzida mudança de distribuição ou de regime. Mesmas dez sementes por condição; rho controla apenas a dependência temporal.

| Correlação rho | Séries com algum log | Total de logs | Alertas |
|---|---|---|---|
| 0.0 | 0/10 | 0 | 0 |
| 0.5 | 10/10 | 37 | 0 |
| 0.9 | 10/10 | 667 | 0 |
| 0.99 | 10/10 | 847 | 0 |

Esses avisos são falsos quanto à hipótese de uma mudança de regime, que não existe no gerador. Podem corresponder a excursões locais do processo correlacionado. O resultado mostra que a baixa taxa no controle independente/embaralhado **não se transfere a qualquer série estacionária**. Não significa alerta indevido de quebra da relação: aqui não há resposta y e todos esses avisos são logs. É um teste exploratório adicional, fora do protocolo original, com dez repetições por condição e sem comparação com concorrentes.

**5. O que as telas ainda não demonstram**

- “Único que responde tudo”: entre as implementações e os adaptadores escolhidos, apenas Sismo fornece todos esses relatórios. As colunas de direção, tamanho e trajetória não foram implementadas para os concorrentes. Isso não estabelece exclusividade universal; tampouco prova que todos os relatórios estejam corretos em produção.
- A recomendação de retreinar ou manter um modelo não foi validada por melhora/manutenção de desempenho de um modelo externo. Os concorrentes no eixo de erro usam uma regressão online, enquanto o Sismo usa sua própria referência com atributos discretizados. A comparação envolve essas escolhas de representação e adaptação.
- A empresa é simulada, com três sementes de vidas normais e três variantes de controle da primeira. Processos, campos, janelas e episódios compartilham mundos; não são todos observações independentes. Há inclusive repetição exata do incidente entre a vida normal da primeira semente e a variante sem defeito. Intervalos binomiais e reamostragem por episódio não capturam toda essa dependência.
- Como ilustração sob independência, 7/10 contingências corresponde a intervalo binomial exato de aproximadamente 34,8% a 93,3%; 10/15 mudanças de regime, de 38,4% a 88,2%. Resultados perfeitos em amostras pequenas não significam incerteza zero. A regra de empate a dois erros padrão não é teste de equivalência.
- Os 2.047 arquivos incluem cópias embaralhadas, variantes de aquecimento e processos da mesma vida. Não equivalem a 2.047 bases reais independentes. Os hashes confirmam integridade e consistência; não comprovam, sozinhos, que o protocolo foi publicado antes de qualquer inspeção dos resultados ou que só houve uma tentativa histórica.

**6. Observação matemática sobre “e-values”**

`detector/evidence.py` zera o log do fator quando ele fica não positivo e reinicia a referência. Consequentemente, os exponenciais retidos são sempre pelo menos um e podem exceder um com probabilidade positiva até sob um nulo Bernoulli estacionário. Eles não satisfazem automaticamente a definição usual de e-value, cuja esperança sob o nulo é no máximo um. Uma simulação diagnóstica com 500 réplicas, p = 0,125, mostrou média 3,50 no item 500, mínimo 1.

Isso não é, isoladamente, uma refutação de toda possível garantia de tempo médio até falso aviso: a teoria de e-detectors utiliza condições e garantias próprias. Mas citar média de e-values não fornece a prova que falta para este procedimento adaptativo e seus reinícios. Não interpretar A = 200.000 como garantia automática de probabilidade de falso aviso de 1/A. Fontes primárias: [Vovk e Wang, definição e combinação de e-values](https://arxiv.org/abs/1912.06116) e [Shin, Ramdas e Rinaldo, e-detectors](https://arxiv.org/abs/2203.03532). Evidências locais: `diagnostico_evalues.json` e os testes temporais acima.

**Recomendação para as telas**

Manter os números confirmados, o primeiro lugar condicionado ao agregado e o veredito “não aprovado”. Atualizar a ordem e as médias dos concorrentes após corrigir a elegibilidade; explicitar as nove versus dez tarefas. Apresentar a direção como “209/209 em mudanças com sinal positivo” e o tamanho como avaliação posterior ao aviso. Tratar “mudanças não rotuladas” como hipótese a validar e acrescentar a limitação de autocorrelação aos controles. A conclusão sustentada é: **bom desempenho nos cenários sintéticos escolhidos, reprodução consistente dos artefatos e limitações operacionais relevantes ainda abertas**.

**Evidências e reprodução**

Arquivos principais nesta pasta: `integridade.json`, `checagem_numerica_independente.json`, `linhas_verificadas.csv`, `reproducao_amostra.json`, `reproducao_publicas.json`, `nab_recalculado.json`, `auditoria_matriz_ranking.json`, `matriz_ranking_corrigida.json`, `ranking_com_tetos_corrigidos.json`, `nulos_temporais.json` e `resumo_evidencias.json`.

Scripts próprios: `verificar_independente.py`, `reproduzir_amostra.py`, `reproduzir_publicas.py`, `recalcular_nab.py`, `auditar_matriz_ranking.py` e `testar_nulos_temporais.py`. Os scripts de download verificam os hashes fixados no projeto. `rank_final.py` foi preservado na pasta `ranking_recebido/ranking/`; a matriz corrigida é um arquivo separado. O recálculo NAB protege resultados existentes e exige uma pasta de trabalho nova para repetir.
