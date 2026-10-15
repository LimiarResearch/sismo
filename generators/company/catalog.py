"""The company catalog: the teams and roles of the 50 people, the workflow projects, the product components and routes, the
customer regions. This is what does not change while the world runs. The seed derivation also lives here: each part of the world
has its own random sequence, derived from the company seed and the name of the part, so that the same seed repeats the same life
and a change in one place does not shift the random draws of another."""
import hashlib
import random

import numpy as np


def seed_of(seed, *names):
    """A 63-bit integer derived from the seed and names; the same in any process and on any machine."""
    h = hashlib.blake2b(("|".join([str(seed)] + [str(n) for n in names])).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big") >> 1


def rng_for(seed, *names):
    return random.Random(seed_of(seed, *names))


def np_rng(seed, *names):
    return np.random.default_rng(seed_of(seed, *names))


# ---------- teams ----------
# The owner and the office administrator form the "gestão" (management) team: no aggregate comes from a single person.
TEAMS = ("produto", "desenvolvimento", "qualidade", "atendimento", "vendas", "operação", "gestão")

# (team, role, headcount, project or work stream)
COMPOSITION = (
    ("produto", "líder de produto", 1, None),
    ("produto", "gerente de produto", 1, "PROD"),
    ("produto", "gerente de produto", 1, "PLAT"),
    ("produto", "designer", 1, "PROD"),
    ("produto", "analista de produto", 1, "PROD"),
    ("desenvolvimento", "líder técnico", 1, "PROD"),
    ("desenvolvimento", "desenvolvedor", 8, "PROD"),
    ("desenvolvimento", "líder técnico", 1, "PLAT"),
    ("desenvolvimento", "desenvolvedor", 5, "PLAT"),
    ("qualidade", "analista de qualidade", 4, "PROD"),
    ("qualidade", "analista de qualidade", 2, "PLAT"),
    ("atendimento", "coordenador de atendimento", 1, "SUP"),
    ("atendimento", "analista de atendimento", 7, "SUP"),
    ("vendas", "gerente de vendas", 1, None),
    ("vendas", "pré-vendas", 2, None),
    ("vendas", "executivo de vendas", 5, None),
    ("operação", "engenheiro de operação", 4, "INFRA"),
    ("gestão", "financeiro", 1, None),
    ("gestão", "pessoas", 1, None),
    ("gestão", "administrativo", 1, None),
    ("gestão", "dono", 1, None),
)

# ---------- workflow ----------
PROJECTS = {"PROD": "Produto", "PLAT": "Plataforma", "SUP": "Suporte", "INFRA": "Infraestrutura"}

# ---------- product ----------
ROUTES = ("login", "catalogo", "busca", "produto", "carrinho", "frete", "pedido", "pagamento", "relatorio", "exportacao", "notas", "conta")
ROUTE_NAME = {"login": "login", "catalogo": "catálogo", "busca": "busca", "produto": "produto", "carrinho": "carrinho",
             "frete": "frete", "pedido": "pedido", "pagamento": "pagamento", "relatorio": "relatório", "exportacao": "exportação",
             "notas": "notas fiscais", "conta": "conta"}
COMPONENTS = ("login", "catalogo", "pedido", "frete", "pagamento", "fiscal", "relatorio", "notificacao", "infra")
COMPONENT_NAME = {"login": "login e conta", "catalogo": "catálogo e busca", "pedido": "pedido e carrinho", "frete": "frete",
                   "pagamento": "pagamento", "fiscal": "fiscal", "relatorio": "relatórios", "notificacao": "notificações",
                   "infra": "infraestrutura"}
ROUTE_COMPONENT = {"login": "login", "conta": "login", "catalogo": "catalogo", "busca": "catalogo", "produto": "catalogo",
                   "carrinho": "pedido", "pedido": "pedido", "frete": "frete", "pagamento": "pagamento", "notas": "fiscal",
                   "relatorio": "relatorio", "exportacao": "relatorio"}
# which squad owns each component
COMPONENT_PROJECT = {"login": "PLAT", "catalogo": "PROD", "pedido": "PROD", "frete": "PROD", "pagamento": "PROD",
                      "fiscal": "PLAT", "relatorio": "PROD", "notificacao": "PLAT", "infra": "INFRA"}

# ---------- customers ----------
PLANS = ("básico", "pro", "empresarial")
# the first digit of the CEP (Brazilian postal code) gives the region
REGIONS = ("São Paulo", "Rio de Janeiro e Espírito Santo", "Minas Gerais", "Norte e Nordeste", "Centro-Oeste", "Sul")
DIGIT_REGION = {"0": 0, "1": 0, "2": 1, "3": 2, "4": 3, "5": 3, "6": 3, "7": 4, "8": 5, "9": 5}
# Brazilian states by first CEP digit (for the fiscal note)
STATES_BY_DIGIT = {"0": ("SP",), "1": ("SP",), "2": ("RJ", "ES"), "3": ("MG",), "4": ("BA", "SE"), "5": ("PE", "AL", "PB", "RN"),
                 "6": ("CE", "PI", "MA", "PA", "AM", "AP", "RR", "AC"), "7": ("DF", "GO", "TO", "MT", "MS", "RO"),
                 "8": ("PR", "SC"), "9": ("RS",)}

MINUTES_PER_DAY = 1440
