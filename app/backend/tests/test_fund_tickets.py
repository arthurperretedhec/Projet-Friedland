"""Tickets par société de gestion (data/fund_tickets.csv, fourni par Alexandre le 2026-11-27).

Valeurs attendues recopiées à la main du classeur Friedland_tickets_fonds_complete.xlsx
(onglet Tickets).
"""

import pytest

from app.data.fund_tickets import FundTicket, choose_ticket, load_fund_tickets


@pytest.fixture(scope="module")
def tickets():
    return load_fund_tickets()


def test_every_fund_of_the_workbook_is_loaded(tickets):
    # 89 fonds ont un ticket dans le classeur (112 - 23 laissés vides), 117 tickets en tout.
    assert len(tickets) == 89
    assert sum(len(v) for v in tickets.values()) == 117


def test_single_ticket_from_the_database(tickets):
    # B4 : Activa Capital, « 10–40 M€ », auteur Base Friedland.
    (activa,) = tickets["fund-003"]
    assert (activa.min_eur_m, activa.max_eur_m) == (10, 40)
    assert activa.source_type == "base"
    assert activa.source_url == "https://activa.fr/vision"
    assert activa.to_confirm is False


def test_open_bounds_and_decimal_comma(tickets):
    # B13 : « Antin Flagship : ≥ 400 M€ » ; B14 : Aquiti « ≤ 10 M€ » ; B26 : BTP « 0,5–8 M€ ».
    assert (tickets["fund-012"][0].min_eur_m, tickets["fund-012"][0].max_eur_m) == (400, None)
    assert (tickets["fund-013"][0].min_eur_m, tickets["fund-013"][0].max_eur_m) == (None, 10)
    assert (tickets["fund-025"][0].min_eur_m, tickets["fund-025"][0].max_eur_m) == (0.5, 8)


def test_internal_source_keeps_no_project_name(tickets):
    # B5 : Adagia, intelligence interne : les noms des dossiers clients ne sont pas recopiés.
    (adagia,) = tickets["fund-004"]
    assert adagia.source_type == "internal"
    assert adagia.source_url == ""


def test_third_party_web_source_is_flagged(tickets):
    # B27 : Butler, « Mergr (source tierce, à confirmer) ».
    (butler,) = tickets["fund-026"]
    assert butler.source_type == "web"
    assert butler.to_confirm is True


def test_choose_the_ticket_of_the_best_strategy(tickets):
    # B12 : six stratégies Andera ; la meilleure stratégie « andera MidCap » -> 40–120.
    t = choose_ticket(tickets["fund-011"], "andera MidCap")
    assert (t.label, t.min_eur_m, t.max_eur_m) == ("andera MidCap", 40, 120)


def test_unlabelled_ticket_comes_first_when_no_strategy_matches(tickets):
    # B25 : Bpifrance « 5–50 M€ ; Bpifrance FIEE 2 : 2–20 M€ » -> le ticket général.
    t = choose_ticket(tickets["fund-024"], "Bpifrance Mid & Large Cap")
    assert (t.min_eur_m, t.max_eur_m) == (5, 50)


def test_no_ticket_for_a_fund_left_empty(tickets):
    # A3 : Access Capital Partners, cellule B vide.
    assert "fund-002" not in tickets
    assert choose_ticket((), "anything") is None


def test_invalid_rows_are_refused(tmp_path):
    header = (
        "fund_id,management_company,order,label,min_eur_m,max_eur_m,"
        "source_type,source_url,to_confirm\n"
    )
    for row, message in [
        ("fund-x,X,0,,20,10,base,,no\n", "minimum"),
        ("fund-x,X,0,,,,base,,no\n", "bound"),
        ("fund-x,X,0,,1,2,guess,,no\n", "source_type"),
    ]:
        (tmp_path / "fund_tickets.csv").write_text(header + row, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_fund_tickets(tmp_path)


def test_missing_file_means_no_ticket(tmp_path):
    assert load_fund_tickets(tmp_path) == {}


def test_fund_ticket_is_immutable():
    t = FundTicket("", 1, 2, "base", "", False)
    with pytest.raises(AttributeError):
        t.min_eur_m = 3  # type: ignore[misc]
