
[BACK](https://github.com/jacs121/One-Lucid-Night)

the waves are controlled via the `waves.json` file it contains a list of all waves with each element being a list of the entity selectors that provide the enemies, items and runes that will spawn at that wave

a item selector looks like this:
```json
{
    "type": "item",
    "items": "list of what item this can spawn",
    "position": "2 number selectors",
    "...": "..."
}
```

a enemy selector looks like this:
```json
{
    "type": "enemy",
    "enemies": "list of what enemy this can spawn",
    "position": "2 number selectors",
    "...": "..."
}
```

and a rune selector looks like this:
```json
{
    "type": "rune",
    "runes": "list of what rune this can spawn",
    "position": "2 number selectors",
    "...": "..."
}
```

the first argument called `type` is specifying what this is (is it an item, is it an enemy, or is it a rune)

the second argument is specific to each `type` and is giving a list of what has the possibility to actually spawn, meaning it picks a random name within the list (this argument only takes the actual names of what to spawn and not exactly the class name for example: "AmmoBoxItem" -> "AmmoBox")

the second argument is the `position` which is a 2 number long list for `(x, y)` and each side is calculated based on what it is set to:
* using `{"min": A, "max": B}` would give a random number from `A` to `B`
* using `"l"`, `"r"`, `"t"`, or `"b"` would return the left, right, top, or bottom of the map based on the letter
* using `[A, B, C, ...]` would choose a random element from the list
* finally using any number would just return that number unchanged
each of these calculations can be stacked for fine control

any other arguments would be past down into what ever you are spawning for example: max health, speed, and what ever else