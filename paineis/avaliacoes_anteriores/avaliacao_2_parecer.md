# Avaliação independente do benchmark Sismo

Data: 18/10/2026. Material avaliado: exclusivamente os dois pacotes fornecidos e os dados/código NAB nas origens fixadas pelo pacote. O código do benchmark foi preservado; os scripts e resultados desta avaliação estão em `audit/`.

## Conclusão

Os resultados publicados são internamente consistentes e as linhas e o ranking podem ser recalculados a partir das saídas fornecidas. O veredito do protocolo continua **não aprovado: 10 das 18 linhas que decidem passaram**. Isso não equivale a validar todas as interpretações científicas ou as implementações dos concorrentes.

Encontrei problemas adicionais às pendências informadas: o CJSD está desativado nas bases sem resposta; o adaptador ponderado do WATCH usa dados futuros; e M3 permite contar um mesmo registro de novo normal para várias mudanças. Esses problemas precisam acompanhar a publicação atual como limitações concretas e motivam uma versão corrigida da comparação. Não recomendo apresentar o primeiro lugar como superioridade geral validada.

As ressalvas já presentes nas telas sobre S4a, S4b, S3 e as hipóteses sobre bases públicas melhoram substancialmente a precisão do texto. As seis pendências do repositório foram tratadas como pendências já conhecidas, não como descobertas desta revisão.

## Verificações executadas

| Verificação | Resultado |
|---|---|
| Integridade dos arquivos de publicação | Os 66 arquivos de `frozen_publication.sha256` conferem; o próprio manifesto tem o hash publicado `7de3ed49…` |
| Sementes | Recalculadas do manifesto original: as 30 sintéticas e as três da empresa conferem |
| Cópias de painéis nos dois pacotes | Dez imagens, LEIAME, script e JSON de ranking idênticos byte a byte |
| Integridade dos três arquivos ZIP internos | CRCs verificados, sem erro |
| Aprovação original versus publicação | 2.047 séries comparadas, 2.047 idênticas, nenhuma diferente ou ausente; tempos de máquina excluídos conforme o comparador |
| Linhas e NAB dos dois arquivos fornecidos | Idênticos após tradução; três linhas L4 com n=0 acrescentadas na publicação |
| Recálculo das 26 linhas | Igualdade exata do JSON usando Python 3.11.9 e NumPy 2.4.6 |
| Manifesto de avisos | As 2.047 linhas e hashes conferem; diferenças de terminador de linha do Windows desconsideradas |
| Tabela | Tabela recalculada igual à publicada, desconsiderados terminadores de linha |
| Ranking | JSON recalculado exatamente igual: Sismo 3,30; DDM 3,60; HDDM_A 3,60; cinco primeiros lugares, incluindo empates |
| Reexecução amostral do detector | Seis séries sintéticas regeneradas e reexecutadas: avisos, relatos e eventos exatamente iguais aos arquivados |
| Recálculo pelo motor oficial NAB | Os 29 scores das 36 séries e os 15 scores das 58 séries conferem nas duas casas publicadas; Sismo 14,27 e 16,27 |

Uma primeira passagem usou Python 3.13.3 / NumPy 2.4.2. Houve 82 diferenças de arredondamento em campos auxiliares (`false_per_day` e `field_cover`), no máximo 7,11×10⁻¹⁵, sem diferença nos números apresentados ou vereditos. A passagem posterior em Python 3.11 / NumPy 2.4.6 eliminou todas elas. Não são divergências do benchmark.

Os ambientes isolados, scripts de auditoria e logs permitem distinguir recálculo dos resultados, reexecução amostral e testes adicionais. Não executei as aproximadamente 15 horas do comando Linux completo, nem reconstruí o HTM, nem regenerei as seis vidas completas. A comparação dos dois arquivos de rodadas não substitui essa reexecução integral.

A amostra reexecutada usa a semente de aprovação 123190 e as famílias `cov`, `num_real`, `null_num`, `mc_cov`, `ramp_all` e `xor`. O ambiente tem NumPy 2.4.6, SciPy 1.17.1 e river 0.26.1, nas versões do pacote; Python 3.11.9 no Windows, em vez de 3.11.17 no Linux. Não representa reexecução dos demais concorrentes nem das demais sementes. Evidência em `rerun_sample.json`.

Para o NAB, baixei e verifiquei os hashes dos 77 arquivos fixados de dados e código; usei as bibliotecas de `requirements-nab.txt` e o motor oficial, limitando somente o paralelismo a quatro trabalhadores. Os 44 scores foram recalculados a partir dos avisos arquivados. A maior diferença absoluta foi 8,53×10⁻¹⁴, compatível com arredondamento/soma em ordem diferente; todas as duas casas decimais conferem. Isto verifica a pontuação oficial, não reexecuta os detectores que produziram os avisos. Evidências: `nab_recalculado.json`, `nab_engine.log` e `final_summary.json`.

## 1. CJSD nunca pode emitir aviso sem resposta — prioridade alta

Referências: `competitors/methods.py:207–229`, `runner/run.py:96–104`, `runner/calibrate_cjsd.py:13–17`.

O protocolo diz que, sem resposta, o CJSD usa apenas o eixo de entrada. O código envolve **também o teste de entrada** no bloco `if tau is not None`. Entretanto, a calibração guarda D apenas quando z>3; sem resposta `_cjsd_block` devolve D=0 e z=0, a lista D fica vazia e `configs_for` define `tau=None`. O teste `Ix > tau_x` torna-se inalcançável.

Confirmei zero avisos do CJSD em todas as 1.047 saídas sem resposta: NAB (166, incluindo variantes), SMD (30), SMAP (45), MSL (20) e empresa (786). Isso não demonstra que o método calibrado corretamente seja conservador: o adaptador não permite disparar.

O teste mínimo em `focused_checks.py` mantém exatamente os mesmos valores de um bloco: D=0, z=0 e Ix=1, acima de tau_x=0,1. Com tau=None, sai lista vazia; habilitando somente o ramo externo com tau=0, sai um log em 2.999. O teste separa esse defeito de qualquer discussão sobre qualidade da floresta aleatória ou calibração.

Também executei os blocos reais, sem substituir a floresta: uma série gaussiana muda de média 0 para 10 após o aquecimento de 2.000 itens. Com o tau_x padrão de NAB, os blocos têm Ix≈0,69215, muito acima de 0,00013349. Mesmo assim o código original não emite aviso. Habilitar o ramo de entrada produz aviso em 2.999. Esse controle usa scikit-learn 1.9.1, a versão fixada, e está em `rerun_sample.json`.

Consequências: células zero do CJSD nas bases públicas e na empresa não são uma avaliação válida da adaptação declarada; a comparação de SMD contra o único concorrente elegível, com valor zero, é especialmente afetada. O ranking usa essa elegibilidade e também precisa ser revisto. Os resultados sintéticos do CJSD não são invalidados por este defeito específico, pois ali D não está vazio.

Correção proposta: condicionar apenas o ramo de relação a `tau is not None`, deixando o ramo de entrada depender de tau_x. Recalibrar e reajustar o CJSD na parte de desenvolvimento e reexecutar a parte de aprovação afetada, sob nova versão. Não editar silenciosamente a rodada congelada ou substituir somente os números finais. Não é possível prever o novo ranking sem essas rodadas.

## 2. WATCH ponderado usa informação futura — prioridade alta

Referências: `competitors/methods.py:254`, `:271`, `:275`.

`Xct` contém todo o restante da série. O adaptador ajusta `StandardScaler().fit(Xct)` antes da adaptação e, nas primeiras observações do alvo, usa `Xs[ad:ad+10]`, que pode incluir até nove observações ainda futuras. A escala calculada com o sufixo participa da regressão logística regularizada; não é apenas uma transformação de exibição.

Fiz um teste de causalidade com duas séries de 6.000 observações, idênticas até o item 4.999 e diferentes somente a partir de 5.000. Usando o mesmo y, a mesma semente e o código real do adaptador, a martingala ponderada já difere no item **2.120**. Há 2.880 valores diferentes antes do ponto em que os dados começam a divergir. Evidência: `watch_prefix.py` e `watch_prefix.json`.

O teste comprova uso de futuro no cálculo; não quantifica quantas decisões finais do benchmark mudariam. Há também avisos numéricos de overflow no cenário de estresse, que não usei para inferir nada sobre os arquivos publicados. O primeiro desvio de prefixo e a inspeção do código são a evidência relevante.

Correção proposta: ajustar a escala somente no histórico disponível e construir o alvo somente com observações já vistas; verificar invariância de prefixo antes de recalibrar e reexecutar. O defeito é do adaptador avaliado, e não uma conclusão sobre o algoritmo WATCH original. A avaliação não deve ser descrita como uma comparação inteiramente causal enquanto esse ponto permanecer.

## 3. M3 reutiliza o mesmo registro para várias mudanças — prioridade média

Referência: `metrics/rows.py:417–429`. A linha procura, para cada mudança, qualquer `became_new_normal` no mesmo campo até 15 dias depois. Não exige associação ao episódio correto, correspondência exclusiva nem interrupção da janela quando ocorre outra mudança.

Caso concreto em `normal_s479019`:

| Processo | Mudanças verdadeiras (minuto) | Um único registro aceito para todas |
|---|---|---|
| rota catálogo | 12.446, 12.501, 12.676 | 26.700 |
| rota notas fiscais | 25.408, 25.457, 32.610 | 38.800 |

Assim, os **10 acertos de M3 estão sustentados por seis registros distintos**, contando cada vida separadamente. Não são dez mudanças individualmente reconhecidas por dez confirmações. Além disso, a mesma mudança em 12.436 e sua confirmação em 18.600 reaparecem nas variantes da primeira semente.

O número 10/15 reproduz a regra escrita; não é um erro de soma. É uma limitação adicional à dependência entre vidas/processos já informada. Proponho associar previsões aos episódios, impedir múltiplos créditos para a mesma confirmação e tratar reversões próximas explicitamente em uma versão futura. Na publicação atual, explicar o que 10/15 significa e evitar apresentar os 15 casos como ensaios independentes. Reamostrar episódios ou usar erro binomial sem considerar a vida não resolve a dependência.

## 4. Autocorrelação: a limitação conhecida precisa aparecer na interpretação das telas

Teste adicional ao protocolo, sem alterar parâmetros: AR(1) gaussiano com média zero, variância um, x₀ já sorteado da distribuição estacionária e inovação com desvio √(1−ρ²); 20.000 itens; sementes 0 a 4; Monitor padrão, um campo, sem resposta. Não há degrau, tendência, mudança de parâmetro ou aquecimento inicial fora da distribuição estacionária.

| ρ | Logs nas cinco séries | Alertas |
|---|---|---|
| 0 | 0, 0, 0, 0, 0 | 0 |
| 0,8 | 52, 39, 49, 48, 45 | 0 |
| 0,95 | 77, 73, 79, 75, 74 | 0 |

Isso confirma de forma independente a pendência informada. É um teste de estresse pequeno, não uma estimativa populacional. O caso ρ=0 é controle. Os alertas zero sem y não testam a capacidade de separar quebra de relação: nesse modo o benchmark não oferece uma resposta real ao detector.

O embaralhamento destrói a dependência temporal, além de remover mudanças de regime. Portanto, observar zero avisos nas séries embaralhadas não distingue mudanças reais sem rótulo de reação à autocorrelação. A hipótese sobre mudanças reais pode permanecer como hipótese, mas esse mecanismo alternativo deve aparecer ao lado dela. O título “Por que ela não passa” ainda apresenta uma explicação causal mais conclusiva que os dados.

Na tela de placar, “fica quieto em séries sem mudança — 0 de 370 rodadas com alerta” deixa os logs fora do destaque. A formulação mais fiel é: “Nos nulos sintéticos do protocolo: 0/370 com alerta e 6/370 com log; não inclui os nulos estacionários autocorrelacionados”.

## 5. Ranking: reproduzível, exploratório e sensível à composição

As regras do script são explícitas; não encontrei divergência no resultado publicado. Ainda assim:

- O ranking não foi um critério congelado de aprovação. A apresentação deve qualificá-lo como resumo exploratório posterior.
- As posições usam empates na melhor posição e dão a todos os inelegíveis a posição “número de elegíveis + 1”. Em SMD, Sismo recebe posição 2 porque só o CJSD é elegível — justamente o adaptador desativado. Isso não significa ser o segundo melhor F1 válido de SMD.
- Os denominadores variam: alguns métodos têm nove tarefas; outros dez; HTM e CTM ficam fora por cobertura. A nota explica isso, mas “nas mesmas dez tarefas” no subtítulo simplifica demais.
- Escolhe-se por tarefa a melhor configuração elegível entre padrão e ajustada, após observar o valor de aprovação. Isso está declarado e é aplicado aos concorrentes, mas resume um envelope de configurações, não uma configuração operacional única escolhida antes da aprovação.
- Diferença de média de posição de 0,3 não vem acompanhada de inferência de superioridade global. As tarefas reutilizam dados e não são dez experimentos independentes.

Como análise de sensibilidade, mantendo as posições já calculadas e apenas retirando uma tarefa, sem reajustar métodos: sem S3, DDM fica em 3,22 e Sismo em 3,56; sem S5, HDDM_A fica em 2,78, HDDM_W em 3,00 e Sismo em 3,56. Isso não propõe excluir essas tarefas; mostra que o primeiro lugar depende do conjunto e dos pesos escolhidos. Evidência em `detail.json`, chave `rank_sensitivity`.

Sugestão de título: “Menor posição média neste ranking exploratório”. Manter junto o veredito 10/18 e a cobertura de cada método. Com os defeitos dos adaptadores, acrescentar que o ranking é da implementação arquivada e requer nova comparação para sustentar uma conclusão corrigida.

## 6. Alcance das métricas e ajustes nas telas

**S3.** A ressalva nova está correta: exige que os campos acusados sejam verdadeiros, sem exigir todos os campos verdadeiros. Confirmei 478/480 nesse critério. Para tornar a diferença concreta: igualdade exata entre conjunto acusado e conjunto verdadeiro ocorre em **308/480**. Em `ramp_all`, mudam os 20 campos; a linha dá 30/30 acertos, mas a cobertura média é 6,17% dos campos e nenhum dos 30 casos identifica o conjunto completo. Isso não invalida o critério declarado; limita “diz qual campo mudou”. Uma futura linha com precisão e cobertura é mais informativa.

**S4a.** A linha reproduz 209/209, mas o próprio classificador constante “subiu” também obtém 100%. A nota corrige a interpretação, porém passar contra 50% não demonstra discriminação entre subidas e quedas. Manter o resultado histórico e descrever a linha como verificação unilateral; testar ambas as direções em versão nova.

**S4b.** Reproduz 179/179. O valor é lido 500 itens depois do aviso, condicionado a haver um aviso válido e um relato do campo verdadeiro; o código para no primeiro campo verdadeiro utilizável. Não é 100% de todos os campos de todas as mudanças, nem precisão no instante do alarme. A correção de tempo está nas telas; eu acrescentaria a condição e o denominador no painel de recursos.

**Quando começou.** Os 71,2% de Sismo no painel de recursos correspondem a **341/479 mudanças detectadas**, não a uma métrica de localização do início sobre todas as mudanças possíveis. A tolerância é 500 itens nos sintéticos. A nota diz “mudanças achadas”, mas omite a largura. Acrescentar “entre as detectadas, tolerância de ±500 itens”; comparar percentuais condicionais sem suas quantidades pode favorecer métodos que detectam poucos casos fáceis.

**Trajetória.** Os 97,8% da coluna são S4c, 176/180 para `became_new_normal`. Não são uma acurácia de todos os estados da trajetória: a volta ao normal falha em M5 e a deriva da carteira falha em M4. Renomear a coluna para “novo normal nos degraus sintéticos” evita generalização.

**Retorno.** A linha tem sete episódios elegíveis; apenas cinco têm retorno tardio observado. Os 11–14 h descrevem esses cinco, não todos os sete. Proponho escrever “5/7 retornos observados em 11–14 h; 0/7 dentro de 3 h”.

**Limite L4.** A linha de SMD detecta 9/127 eventos curtos (cerca de 7,1%) e declara “limite não confirmado” por superar o CJSD elegível com zero, mesmo com Sismo acima do teto público. Isso é coerente com a regra formal usada nessa linha, porém não sustenta dizer que a dificuldade de spikes foi resolvida. É particularmente afetada pelo defeito do CJSD. Manter o rótulo histórico com a ressalva e o denominador, ou dar preferência ao texto descritivo de baixa sensibilidade.

**“Único aqui que responde a tudo”.** A expressão “aqui” limita a comparação aos adaptadores presentes, o que é adequado. Eu ainda qualificaria como formatos de saída/capacidades implementadas, não qualidade comprovada em todas as dimensões. O estudo não demonstra exclusividade frente ao campo inteiro nem benefício operacional da combinação com um detector de anomalias. Essa combinação é proposta de uso, não um experimento realizado.

## 7. Pontos metodológicos e de documentação

**E-values.** A ressalva informada precisa alcançar também os comentários de `detector/evidence.py`, `detector/decision.py` e a descrição no protocolo, não só o README. Chamar os escores de fatores de Bayes com reinício descreve melhor o cálculo. A média de escores não adquire validade por receber o nome de e-value; uma garantia sequencial exige a validade do processo sob a classe nula especificada e em tempos de parada. Referência teórica: Ramdas, Ruf, Larsson e Koolen, [Testing exchangeability: fork-convexity, supermartingales, and e-processes](https://arxiv.org/abs/2102.00630). Não há suporte apresentado para interpretar A=200.000 como probabilidade 1/A de falso alarme neste algoritmo.

**“Empatou” não demonstra equivalência.** O protocolo classifica como empate uma diferença que não excede dois erros-padrão e aceita o empate como aprovação. Esse é o critério operacional registrado. Não é um teste de equivalência com margem predefinida e potência demonstrada. Especialmente com poucos episódios da empresa, evitar “tão bom quanto” como inferência estatística. Comparações globais de rankings também exigem tratamento próprio; ver a discussão de comparação entre vários métodos e bases de [Demšar, JMLR 2006](https://www.jmlr.org/papers/v7/demsar06a.html).

**F1 e janelas.** O F1 por evento usado aqui conta vários avisos dentro da mesma janela como um evento e estende a janela de SMD/SMAP/MSL pela duração do evento, com mínimo de dez itens. Uma única previsão pode servir a eventos com janelas sobrepostas. As regras são públicas, mas os números não devem ser comparados diretamente com F1 por ponto ou outras avaliações publicadas. O score NAB oficial é reportado separadamente, como deve ser.

**Cronologia do congelamento.** O protocolo documenta v1 antes do desenvolvimento e v2 depois dele, antes da aprovação. Logo, “protocolo congelado antes de qualquer rodada”, nas telas e na abertura do README, é impreciso para o manifesto de aprovação citado. Sugestão: “protocolo inicial registrado antes do desenvolvimento; versão de aprovação congelada antes da rodada de aprovação”.

**O hash verifica conteúdo, não data.** O pacote permite verificar a publicação atual e derivar sementes. Não contém o código original completo em português que corresponda, arquivo por arquivo, ao manifesto histórico; tampouco prova externa de quando esse manifesto foi fixado. Não encontrei uma contradição que demonstre alteração posterior. O limite é de auditabilidade: acrescentar o arquivo/tag imutável da versão original e uma referência pública datada ao compromisso fortalece a alegação de pré-registro. Igualdade das duas saídas não prova sozinha independência temporal do protocolo.

**Bases públicas.** Não há evidência suficiente para chamar os avisos extras de mudanças reais sem rótulo. O README original da [base SMD](https://github.com/NetManAIOps/OmniAnomaly) descreve os trechos de treino/teste e os rótulos de anomalia do teste; isso não oferece uma verdade de mudanças de regime para validar a explicação. A hipótese não deve servir para descartar a reprovação prevista no próprio protocolo.

## 8. Encaminhamento sugerido

1. Aplicar as pendências documentais já conhecidas, preservando o registro histórico e indicando a data das ressalvas.
2. Acrescentar os defeitos concretos do CJSD e WATCH às limitações da rodada arquivada. Apresentar seus zeros/valores como resultados daquela implementação, não avaliações conclusivas dos métodos.
3. Ajustar os textos dos painéis: natureza exploratória do ranking, 6/370 logs, tolerância e condicionamento das métricas, alcance de M3 e apenas cinco retornos tardios.
4. Publicar uma versão nova para corrigir adaptadores e métricas alteradas, recalibrar no desenvolvimento e avaliar com aprovação nova, preservando integralmente esta rodada. Não reclassificar silenciosamente os 10/18 históricos.
5. Acrescentar nulos estacionários autocorrelacionados e sazonais, subidas e quedas, cobertura dos campos, associação exclusiva de episódios e mais vidas independentes. Pré-especificar o resumo global antes da próxima aprovação.

É possível publicar esta rodada como registro transparente de um benchmark que não passou, com suas ressalvas. Eu não endossaria, no estado atual, os painéis como demonstração concluída de superioridade geral ou como comparação já validada de todos os 15 concorrentes.

## Evidências locais

- `integrity.json`, `compare_runs.log`, `compare_rows.log`: integridade e equivalência entre as rodadas fornecidas.
- `rows_python311.json`, `rows_python311.log`: recálculo completo das métricas a partir das saídas, em Python 3.11.
- `ranking_recalculado.json`: reprodução do ranking publicado.
- `focused_checks.json`: prova mínima do ramo desativado do CJSD, avisos por base, associação M3 e denominadores de localização temporal.
- `detail.json`: cobertura de campos por família e sensibilidade da composição do ranking.
- `stationary_ar1.json`, `probe.py`: teste de estacionariedade/autocorrelação fora do protocolo.
- `watch_prefix.json`, `watch_prefix.py`: teste de uso de futuro no adaptador ponderado.
- `rerun_sample.json`, `rerun_sample.py`: regeneração/reexecução amostral do detector e controle real do CJSD.
- `nab_recalculado.json`, `nab_engine.log`, `recompute_nab.py`: recálculo dos 44 scores pelo motor oficial NAB.
- `final_summary.json`: verificações finais e confirmação de que o manifesto do código original continua válido.

As propostas de alteração metodológica são para uma versão nova. As verificações adicionais desta revisão não foram incorporadas aos critérios históricos nem ao cálculo de 10/18.
