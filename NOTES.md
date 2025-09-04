На 11 июля 2025 (текущая дата):
ВЧЕРА: 1744213200 (10 июля 2025 00:00:00 МСК)

СЕГОДНЯ: 1744299600 (11 июля 2025 00:00:00 МСК)

ЗАВТРА: 1744386000 (12 июля 2025 00:00:00 МСК)

git ls-files --exclude-standard -- ':!:**/*.test.ts.snap' ':!:**/*.test.ts' ':!:**/*.test.tsx' ':!:**/*.test.tsx.snap' ':!:.idea' ':!:**/*.eslintrc' ':!:package-lock.json' ':!:**/*.svg' ':!**/*.png' ':!**/*.jpg'  | xargs wc -l

{
    "extensionProgress": "Success",
    "levelInfo": {
        "currentXp": 1564, # текущий xp
        "currentXpUpperBound": 4200, # xp сколько нужно всего для следующего lvl
        "level": 61, # твой текущий лвл 
        "levelVersion": 360, # беру от матча
        "prestigeLevel": 0, #уровень преданности 
        "totalXp": 190234 # сколько у тебя всего xp всего
    },
    "xpGainBreakdown": {
        "baseMatchXp": 583, # xp за этот матч
        "consecutiveMatchMultiplier": 1, # множитель последовательности матчей
        "emblemsBonus": 18, # бонус от эмблем
        "firstMatchBonus": 300 # бонус первого матча
    }
}

выдача награды в /extensions/playerLevels/earnPlayerXp

{
    "extensionProgress": "Success",
    "grantedCurrencies": [
        { "currency": "Cells", "balance": 777 },
        { "currency": "Shards", "balance": 666 },
        { "currency": "Bloodpoints", "balance": 1488}
    ],
    "levelInfo": {
        "currentXp": 1564, # текущий xp
        "currentXpUpperBound": 4200, # xp сколько нужно всего для следующего lvl
        "level": 61, # твой текущий лвл 
        "levelVersion": 360, # беру от матча
        "prestigeLevel": 0, #уровень преданности 
        "totalXp": 190234 # сколько у тебя всего xp всего
    },
    "xpGainBreakdown": {
        "baseMatchXp": 583, # xp за этот матч
        "consecutiveMatchMultiplier": 1, # множитель последовательности матчей
        "emblemsBonus": 18, # бонус от эмблем
        "firstMatchBonus": 300 # бонус первого матча
    }
}

Награды:

За каждый новый level → +100 Shards.

За каждый 10-й level → +50 Cells.

За новый prestige → +500 Cells, +2000 Shards.

Стремная работа лвлов, щас хз как они работают, чет не синхронизированы нихуя + есть ебейший дюп т.к нет проверки существования матча

Произвести очистку кода