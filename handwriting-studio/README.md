# Handwriting Studio

Upload photos of your handwriting and the app builds a library of your letters. It tells you
which letters, numbers and symbols need more pictures, then writes any text in your hand.

It's one file, [`index.html`](index.html). Open it in any browser (phone or computer). There's no
server and no account. Photos are processed on your device and never uploaded anywhere.

## How it works

1. **Coverage** shows how ready your library is and lists what needs more pictures, most
   important first. It also writes a **practice page** for you, with words picked to cover the
   characters you're missing.
2. **Add photos**: write the practice page (or anything else) on plain paper, photograph it,
   and type what you wrote. The app finds each letter, matches it to your text, and shows them
   for you to check before saving.
3. **Library** shows every saved sample. Odd-looking ones (likely bad cuts) get an orange outline.
4. **Write** turns typed text into an image in your handwriting. Each letter is picked at random
   from your samples, with a little natural wobble, so repeated letters don't look stamped.

### How it decides what needs more pictures

- **Every character has a target.** Common letters need more versions (`e` needs 8) because they
  repeat a lot and identical copies are easy to spot. Rare ones need fewer (`z` needs 4). Capitals
  and numbers need 3; most symbols need 2.
- **Missing beats few.** A character with no samples can't be written at all, so it ranks first.
- **Consistency counts.** If your samples of one letter vary a lot in size or shape, it's marked
  *uneven* and asks for more, so your usual shape wins.
- **Joined-up writing.** Turn on the cursive option and it also tracks common whole words
  (`the`, `and`, `ing`...), since joined letters can't be cut apart cleanly. Whole-word samples
  are used automatically when writing.

## Tips for good photos

- Plain white paper, dark pen. Lined paper can confuse the letter finder.
- Leave clear gaps between words and between lines.
- Shoot straight on in even light, with the writing filling most of the frame.

## Honest limits

- This is a **sample library**, not an AI that invents new strokes. It reproduces the letters you
  photographed. That's why it looks like you, and why coverage matters.
- Print-style writing works best. Cursive letters that touch are saved as whole words or letter
  groups; new words made from single letters won't have your joins.
- Samples are stored in the browser. Use **Library > Save backup file** now and then.

## Put it on your phone

Host the folder anywhere static (for example GitHub Pages), open it in Safari, then
**Share > Add to Home Screen**.
