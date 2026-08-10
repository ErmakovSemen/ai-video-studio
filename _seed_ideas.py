"""Seed the chayniy 'Идеи' column with render-ready, fact-checked scenarios.
Writes scenarios/chayniy/<key>.json for each idea AND adds an Idea card linking to it."""
import os, sys, json
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from studio import boardsync

STYLE = ("Japanese sumi-e ink brush illustration, fine pen and ink linework with bold "
         "confident strokes and variable line weight, black ink only on white background, "
         "occasional diluted ink wash for depth (monochrome only, NO color), large empty "
         "white space, single clear focal subject, wabi-sabi, ukiyo-e inspired, hand-drawn "
         "spontaneous feel, vertical 9:16")
CHARS = {"panda": "assets/chayniy/panda_ink.png", "panda_face": "assets/chayniy/panda_face.png",
         "teacup": "assets/chayniy/teacup_steam.png", "tealeaf": "assets/chayniy/tealeaf.png"}
ENDCARD = {"title": "ЧАЙНЫЙ", "sub": "Истории о чае и замедлении.",
           "vo": "Завари чашку — и почувствуй разницу."}

def sc(image, refs, motion, vo, caption):
    return {"image": image, "refs": refs, "motion": motion, "vo": vo, "caption": caption}

IDEAS = [
 ("puerh_wine", "Чай, который стареет как вино", "Стареет как вино",
  "Пуэр прессуют в диск и оставляют дозревать годами — он ферментируется, мягчает и дорожает, как вино.", [
   sc("a red panda holds an old pressed round tea cake in both paws, looking at it with respect, bold sumi-e ink, white space",
      ["panda"], "slow zoom in on the cake", "Почти любой чай хотят пить свежим. Но не этот.", "Не для свежести"),
   sc("a round pressed tea cake on a wooden shelf beside other aged cakes, bold ink, white background",
      [], "slow pan across the shelf", "Это пуэр — его прессуют в плотный диск и оставляют дозревать.", "Пуэр — диск"),
   sc("close-up of an old tea cake with a faint cobweb, marks of age, bold ink lines, white space",
      [], "very slow push in", "Год за годом он медленно ферментируется и становится мягче и глубже.", "Зреет годами"),
   sc("a single small tea cake under a spotlight like an auction lot, bold sumi-e ink, white background",
      [], "gentle hold, slight zoom", "Старые диски ценятся как вино — за редкие платят тысячи.", "Как вино"),
   sc("a red panda calmly sips dark aged tea, serene, bold sumi-e ink, white space",
      ["panda", "teacup"], "slow zoom in on the calm face", "Время здесь — не враг. А главный мастер вкуса.", "Время — мастер")]),

 ("cold_brew", "Завари чай холодной водой", "Чай на холодной воде",
  "Холодная заварка за несколько часов даёт мягкий сладковатый чай почти без горечи и с меньшим кофеином.", [
   sc("a red panda curiously looks at a glass jug of tea steeping in cold water with ice, bold sumi-e ink, white space",
      ["panda"], "slow zoom in on the jug", "Чай можно заварить вообще без кипятка. Холодной водой.", "Без кипятка"),
   sc("tea leaves slowly releasing pale ink trails in cold water inside a glass, bold ink, white background",
      ["tealeaf"], "pale trails drift down slowly", "Просто залей лист холодной водой и оставь на несколько часов.", "Несколько часов"),
   sc("split composition: left hot water fast dark swirl, right cold water slow pale swirl, ink, white space",
      [], "gentle reveal of both sides", "Холодная вода тянет вкус медленно — и почти не достаёт горечь.", "Без горечи"),
   sc("a tall glass of clear pale cold-brew tea, calm, bold ink, white background",
      ["teacup"], "slow push in", "Кофеина выходит меньше, а вкус — мягкий и сладковатый.", "Меньше кофеина"),
   sc("a red panda refreshed, sipping cold tea through, content, bold sumi-e ink, white space",
      ["panda", "panda_face"], "slow zoom in", "Идеально в жару. Поставь вечером — будет готово к утру.", "Готово к утру")]),

 ("gongfu", "Один лист — десять чашек", "Десять чашек из горсти",
  "Гунфу-ча: много листа в маленькой гайвани и десятки коротких проливов, каждая чашка на вкус другая.", [
   sc("a red panda with a small gaiwan and several tiny cups arranged in a row, bold sumi-e ink, white space",
      ["panda"], "slow zoom in on the set", "На западе чай заваривают один раз. В Китае — десять.", "Не один раз"),
   sc("a small gaiwan packed full with tea leaves, water being poured in, bold ink, white background",
      [], "water pours in, leaves swell", "В маленькую гайвань кладут много листа и заливают на секунды.", "Много листа"),
   sc("tea being poured quickly from a gaiwan into tiny cups, dynamic ink, white space",
      ["teacup"], "quick pour motion", "Каждый пролив — новая чашка. И каждая на вкус другая.", "Каждая — другая"),
   sc("a row of small cups, the tea color fading from dark to pale left to right, ink wash, white background",
      [], "slow pan across the row", "Первая — яркая, пятая — нежная, десятая — едва уловимая.", "От яркой к нежной"),
   sc("a red panda savours a tiny cup with closed eyes, serene, bold sumi-e ink, white space",
      ["panda", "panda_face"], "slow zoom in", "Один лист раскрывается так, как одной чашкой не успеть.", "Гунфу-ча")]),

 ("silver_needle", "Самый нежный чай — из одних почек", "Только почки",
  "Серебряные иглы (Бай Хао Иньчжэнь) — белый чай из нераскрытых пушистых почек, почти без обработки.", [
   sc("a red panda gently holds a single downy tea bud up to the light, delicate, bold sumi-e ink, white space",
      ["panda"], "slow zoom in on the bud", "Самый деликатный чай в мире делают из одних нераскрытых почек.", "Нераскрытые почки"),
   sc("extreme close-up of fuzzy silver tea buds with fine white down, bold ink, white background",
      [], "very slow push in", "Их зовут серебряные иглы — за белый пушок на кончиках.", "Серебряные иглы"),
   sc("tea buds simply laid out drying under soft sun, minimal, bold ink, white space",
      [], "gentle light shifts", "Почти без обработки: только подвялить и высушить. Ничего лишнего.", "Почти без обработки"),
   sc("a clear glass of very pale tea with buds standing upright, elegant, ink, white background",
      ["teacup"], "buds slowly rise and sink", "Настой светлый и сладкий, с ароматом свежего сена и цветов.", "Светлый и сладкий"),
   sc("a red panda sips gently with a soft expression, peaceful, bold sumi-e ink, white space",
      ["panda", "panda_face"], "slow zoom in", "Самый тихий чай. И, может, самый честный.", "Самый честный")]),

 ("tea_horse_road", "Чай возили по дороге смертников", "Дорога смертников",
  "Чайно-конная дорога: тысячу лет чай несли через гималайские тропы из Юньнани в Тибет, меняя на лошадей.", [
   sc("a tiny red panda with a load walks a narrow mountain ledge above a deep gorge, dramatic scale, bold sumi-e ink, white space",
      ["panda"], "slow pan along the ledge", "Тысячу лет назад чай несли через горы по тропам над пропастью.", "Тропы над пропастью"),
   sc("a winding path clinging to misty cliffs, vast mountains, bold ink wash, white background",
      [], "slow reveal of the winding path", "Это Чайно-конная дорога — из Юньнани в Тибет.", "Чайно-конная дорога"),
   sc("a red panda trades a pressed brick of tea for a sturdy horse, bold sumi-e ink, white space",
      ["panda"], "gentle hold", "Спрессованный чай меняли на сильных тибетских лошадей.", "Чай за коней"),
   sc("a porter panda bent under a towering stack of tea bricks on its back, bold ink, white background",
      ["panda"], "slow zoom in on the heavy load", "Носильщики тащили на себе до ста килограммов чая.", "100 кг на спине"),
   sc("a red panda rests at a mountain pass with a cup of tea, vast view, serene, bold sumi-e ink, white space",
      ["panda", "teacup"], "slow zoom out", "Чай был валютой, лекарством и смыслом всего пути.", "Чай как валюта")]),

 ("blooming_tea", "Этот чай расцветает в чашке", "Расцветает в чашке",
  "Связанный (цветущий) чай — комок листьев с вшитым вручную цветком, который распускается в горячей воде.", [
   sc("a red panda drops a small round bundle of tea leaves into a tall glass, curious, bold sumi-e ink, white space",
      ["panda"], "slow zoom in on the glass", "С виду — просто комок чайных листьев. Но подожди секунду.", "Просто комок"),
   sc("the tea bundle in hot water beginning to slowly unfurl, bold ink, white background",
      [], "the bundle slowly opens", "В горячей воде он медленно раскрывается.", "Раскрывается"),
   sc("a delicate flower blooming inside the glass surrounded by opening tea leaves, elegant ink, white space",
      [], "petals spread outward slowly", "Внутри спрятан цветок — его вшивают в лист вручную.", "Цветок внутри"),
   sc("a full bloom of flower and leaves spread inside a glass like a tiny garden, bold ink, white background",
      [], "gentle drift of petals", "Это связанный чай. Он и напиток, и маленький спектакль.", "Связанный чай"),
   sc("a red panda watches the blooming glass with delight, soft smile, bold sumi-e ink, white space",
      ["panda", "panda_face"], "slow zoom in on the delighted face", "Чай, который сначала смотрят, а потом пьют.", "Сначала смотрят")]),

 ("not_real_tea", "Половина «чая» — вообще не чай", "Это не чай",
  "Чай — только лист Camellia sinensis; ромашка, мята, ройбуш, каркаде — это тизаны, не чай.", [
   sc("a red panda eyes a shelf of jars labelled with herbs and flowers, skeptical tilt, bold sumi-e ink, white space",
      ["panda", "panda_face"], "slow pan across the jars", "Ромашка, мята, ройбуш, каркаде. Вот только это не чай.", "Не чай"),
   sc("a single elegant Camellia sinensis tea branch with leaves, bold sumi-e ink, white background",
      ["tealeaf"], "slow push in on the branch", "Настоящий чай — только с одного куста. Камелия китайская.", "Камелия китайская"),
   sc("one tea leaf in the center with small icons of green black oolong puerh cups around it, ink, white space",
      [], "gentle hold", "Зелёный, чёрный, улун, пуэр — всё это её лист.", "Один куст"),
   sc("dried flowers and herbs in a separate bowl, clearly different from tea leaves, bold ink, white background",
      [], "slow zoom in", "А травяные сборы — это настои. По-научному — тизаны.", "Травы — тизаны"),
   sc("a red panda calmly sips, content and unbothered, bold sumi-e ink, white space",
      ["panda"], "slow zoom in", "Не хуже. Просто, честно говоря, другое.", "Просто другое")]),

 ("high_mountain", "Лучший улун растёт в облаках", "Чай из облаков",
  "Высокогорный улун (гаошань) растёт медленно в холоде и тумане, копит сахара и аромат — сливочный и цветочный.", [
   sc("a tiny red panda stands among misty high mountain tea terraces in the clouds, vast scale, bold sumi-e ink, white space",
      ["panda"], "slow pan across the misty terraces", "Самый ароматный улун растёт там, где живут облака.", "Где облака"),
   sc("tea bushes high on a foggy mountain slope, soft mist, bold ink wash, white background",
      [], "mist drifts slowly", "Высоко в горах холоднее, и чай растёт медленно.", "Растёт медленно"),
   sc("close-up of a thick glossy oolong leaf, detailed veins, bold ink, white space",
      [], "very slow push in", "Медленный рост копит в листе больше сахаров и аромата.", "Больше аромата"),
   sc("a cup of oolong with fragrant floral steam curling up, bold sumi-e ink, white background",
      ["teacup"], "steam curls upward", "Поэтому высокогорный улун такой сливочный и цветочный.", "Сливочный, цветочный"),
   sc("a red panda content with tea on a misty peak, serene, bold sumi-e ink, white space",
      ["panda", "panda_face"], "slow zoom out", "Чем выше гора — тем тише и слаще чай.", "Выше — слаще")]),

 ("tea_with_food", "Не запивай еду чаем", "Не запивай еду чаем",
  "Танины чая мешают усвоению негемового железа из растительной еды — лучше пить чай между приёмами пищи.", [
   sc("a red panda about to sip tea over a plate of food, pausing thoughtfully, bold sumi-e ink, white space",
      ["panda", "panda_face"], "slow zoom in on the pause", "Любишь запивать обед чаем? Тут есть один нюанс.", "Один нюанс"),
   sc("a tea cup above a plate with a dark swirl reaching down, bold ink, white background",
      ["teacup"], "the dark swirl descends", "В чае есть танины — они мешают усваивать железо из еды.", "Танины и железо"),
   sc("ink illustration of plant foods (grains, beans, greens) with an iron symbol, bold ink, white space",
      [], "gentle hold", "Особенно железо из растений: круп, бобов, зелени.", "Железо из растений"),
   sc("a clock beside a tea cup moved aside from a plate, bold sumi-e ink, white background",
      ["teacup"], "the cup slides aside", "Следишь за железом — пей чай между приёмами пищи.", "Между приёмами"),
   sc("a red panda calmly sips tea after a meal, relaxed, bold sumi-e ink, white space",
      ["panda"], "slow zoom in", "Через часик после еды — и чай в радость, и польза.", "Через час — и польза")]),

 ("resteep", "Не выбрасывай заварку после первой чашки", "Не выбрасывай заварку",
  "Хороший крупный лист отдаёт вкус 3–5+ заварок, каждая раскрывает новые оттенки; пыль из пакетика — на одну.", [
   sc("a red panda about to toss used tea leaves into a bin, stopping mid-motion, bold sumi-e ink, white space",
      ["panda", "panda_face"], "freeze on the stopping motion", "Заварил лист один раз и выбросил? Зря.", "Не выбрасывай"),
   sc("good whole loose tea leaves resting in an open teapot, bold sumi-e ink, white background",
      [], "slow push in on the leaves", "Хороший крупный лист заваривают не раз и не два.", "Не один раз"),
   sc("a second and third cup being poured, each slightly different shade, ink wash, white space",
      ["teacup"], "successive pours", "Вторая, третья заварка раскрывают новые оттенки вкуса.", "Новые оттенки"),
   sc("a row of cups showing many infusions in a line, bold ink, white background",
      [], "slow pan across the cups", "Лист может отдавать вкус три, пять, а то и больше раз.", "До 5+ заварок"),
   sc("a red panda happily pours another cup from the same pot, content, bold sumi-e ink, white space",
      ["panda"], "slow zoom in", "А пыль из пакетика выдыхается за одну. Снова — про лист.", "Лист побеждает")]),
]

def main():
    sdir = os.path.join(ROOT, "scenarios", "chayniy")
    os.makedirs(sdir, exist_ok=True)
    board = boardsync.pull("chayniy_content") or boardsync.default_board("chayniy_content")
    ideas_col = next(c for c in board["columns"] if c["id"] == "ideas")
    ideas_col.setdefault("cards", [])
    for key, title, hook, logline, scenes in IDEAS:
        scenario = {"title": title, "hook": hook, "voice": "ru-RU-SvetlanaNeural",
                    "hero": "panda", "brand_image": "assets/chayniy/panda_standing.png",
                    "characters": CHARS, "style": STYLE, "scenes": scenes, "endcard": ENDCARD}
        path = os.path.join(sdir, f"{key}.json")
        json.dump(scenario, open(path, "w"), ensure_ascii=False, indent=2)
        beats = " · ".join(f"{i+1}) {s['caption']}" for i, s in enumerate(scenes))
        desc = (f"🪝 Хук: {hook}\n{logline}\n\nБиты: {beats}\n\n"
                f"✅ Сценарий готов: scenarios/chayniy/{key}.json — осталось сгенерировать.")
        cid = f"idea_{key}"
        card = {"id": cid, "title": title, "desc": desc,
                "scenario": f"scenarios/chayniy/{key}.json", "tags": ["idea", "ready"]}
        ex = next((c for c in ideas_col["cards"] if c.get("id") == cid), None)
        (ex.update(card) if ex else ideas_col["cards"].append(card))
        print("wrote", key)
    ok = boardsync.push("chayniy_content", board, message="board: seed 10 ready ideas")
    print("board pushed:", ok, "| ideas:", len(ideas_col["cards"]))

if __name__ == "__main__":
    main()
