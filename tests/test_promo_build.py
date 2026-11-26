from scripts import promo_build as P


def test_voiced_from_silences_skips_pauses_and_tail():
    v = P.voiced_from_silences([1.0, 3.0], [1.4, 3.2], 5.0)
    assert v == [(0.0, 1.0), (1.4, 3.0), (3.2, 5.0)]


def test_voiced_without_silence_covers_speech():
    assert P.voiced_from_silences([], [], 4.0) == [(0.0, 4.0)]


def test_word_times_are_ordered_and_skip_pause():
    iv = [(0.0, 1.0), (2.0, 3.0)]
    wt = P.word_times("um dois tres quatro", iv)
    assert [w for w, _, _ in wt] == ["um", "dois", "tres", "quatro"]
    starts = [a for _, a, _ in wt]
    assert starts == sorted(starts)
    assert all(not (1.0 < a < 2.0) for _, a, _ in wt)   # nothing starts inside the pause
    assert wt[-1][2] <= 3.0 + 1e-6


def test_caption_chunks_break_on_sentence_end():
    words = [(w, i * 0.3, i * 0.3 + 0.25) for i, w in enumerate("Quer um chatbot? No Flowise voce arrasta".split())]
    chunks = P.caption_chunks(words, 4, 40)
    assert [w for w, _, _ in chunks[0]] == ["Quer", "um", "chatbot?"]


def test_karaoke_event_has_one_kf_per_word():
    ass = P.Ass(1080, 1920)
    chunks = [[("oi", 0.0, 0.3), ("mundo", 0.3, 0.7)]]
    ass.karaoke(10.0, chunks, "Cap", (540, 1500))
    ev = ass.events[0]
    assert ev.count(r"\kf") == 2 and "OI" in ev and "MUNDO" in ev
    assert ",0:00:10.00," in ev


def test_timeline_accounts_for_crossfades():
    starts, total = P.timeline([10.0, 10.0])
    assert starts == [0.0, 10.0 - P.XF] and abs(total - (20.0 - P.XF)) < 1e-9
