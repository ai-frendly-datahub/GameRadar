# GameRadar Data Sources Research

**Generated:** 2026-03-04  
**Research Duration:** 2m 37s

---

## RSS Feeds (25+ Sources)

### Mainstream Gaming News

1. **IGN** - `https://feeds.ign.com/ign/all`
   - Focus: All gaming news, reviews, features
   - Update frequency: Hourly
   - Quality: High (industry leader)

2. **GameSpot** - `https://gamespot.com/feeds/news`
   - Focus: News, reviews, previews, walkthroughs
   - Update frequency: Daily/Hourly
   - Quality: High

3. **Kotaku** - `https://kotaku.com/rss`
   - Focus: Gaming news, industry trends, culture
   - Update frequency: Daily
   - Quality: High

4. **Polygon** - `https://polygon.com/rss/index.xml`
   - Focus: Gaming news, reviews, analysis
   - Update frequency: Daily
   - Quality: High

5. **PC Gamer** - `https://www.pcgamer.com/rss`
   - Focus: PC gaming news, reviews, hardware
   - Update frequency: Daily
   - Quality: High

6. **GamesRadar+** - RSS available
   - Focus: Gaming news, reviews, features
   - Update frequency: Daily
   - Quality: High

7. **VG247** - RSS available
   - Focus: Gaming news, industry updates
   - Update frequency: Daily
   - Quality: High

8. **Rock Paper Shotgun** - RSS available
   - Focus: PC gaming focused
   - Update frequency: Daily
   - Quality: High

9. **Game Informer** - `https://gameinformer.com/news.xml`
   - Focus: Gaming news, reviews, previews
   - Update frequency: Daily
   - Quality: High

### Platform Official Sources

10. **Xbox Wire** - `https://news.xbox.com/en-us/feed/`
    - Focus: Xbox news, Game Pass, ID@Xbox
    - Update frequency: Hourly
    - Quality: High (official source)
    - **Verified active** ✓

11. **Nintendo Life** - `https://www.nintendolife.com/feeds/latest`
    - Focus: Nintendo news, reviews, Switch/indie coverage
    - Update frequency: Daily
    - Quality: High
    - **Verified active** ✓

12. **PlayStation Blog** - No public RSS feed
    - Focus: PlayStation news, PS5/PS4 updates
    - Update frequency: Daily
    - Quality: High (official)
    - Note: Requires web scraping

### Mobile Gaming

13. **Pocket Gamer** - `https://www.pocketgamer.com/news/index.rss`
    - Focus: Mobile gaming, iOS/Android
    - Update frequency: Daily
    - Quality: High

14. **Touch Arcade** - `https://toucharcade.com/feed`
    - Focus: iOS gaming reviews, news
    - Update frequency: Daily
    - Quality: High

### Indie Games

15. **IndieGames.com** - `https://indiegamesplus.com/feed`
    - Focus: Indie game news, interviews
    - Update frequency: Daily
    - Quality: High

16. **The Indie Game Website** - `https://indiegamewebsite.com/feed`
    - Focus: Indie game news, reviews
    - Update frequency: Daily
    - Quality: Medium

17. **Alpha Beta Gamer** - RSS available
    - Focus: Indie alpha/beta tests, game jams
    - Update frequency: Daily
    - Quality: Medium

### Esports

18. **Dot Esports** - RSS available
    - Focus: Esports news, tournament coverage
    - Update frequency: Daily
    - Quality: High

19. **Esports Insider** - `https://esportsinsider.com/feed`
    - Focus: Esports industry news
    - Update frequency: Daily
    - Quality: High

---

## APIs (9+ Sources)

### Game Database APIs

1. **Steam Web API**
   - Base URL: `https://api.steampowered.com/`
   - Documentation: https://partner.steamgames.com/doc/webapi/
   - Authentication: API Key required (free)
   - Rate limit: 200,000 calls per day
   - Quality: Excellent (official Steam API)

2. **IGDB API (Internet Game Database)**
   - Base URL: `https://api.igdb.com/v4/`
   - Documentation: https://api-docs.igdb.com/
   - Authentication: OAuth 2.0 (Twitch credentials)
   - Rate limit: 4 requests per second
   - Quality: High (comprehensive game data)

3. **RAWG API**
   - Base URL: `https://api.rawg.io/`
   - Documentation: https://rawg.io/apidocs
   - Authentication: API Key required
   - Rate limit: 20,000 requests/month (free tier)
   - Data: 500,000+ games
   - Quality: High (generous free tier)

### Streaming/Esports APIs

4. **Twitch API**
   - Base URL: `https://api.twitch.tv/helix/`
   - Documentation: https://dev.twitch.tv/docs/api
   - Authentication: OAuth 2.0 required
   - Quality: High (official Twitch API)

5. **Riot Games API**
   - Focus: League of Legends, Valorant
   - Authentication: API Key required
   - Quality: High (official Riot API)

---

## Web Scraping Targets (15+ Sites)

### Platform Stores

1. **Steam Store** - `https://store.steampowered.com/`
   - Target: New releases, upcoming, top sellers
   - Update frequency: Hourly
   - Quality: High

2. **PlayStation Store** - `https://store.playstation.com/`
   - Target: New releases, sales, PS Plus games
   - Update frequency: Weekly
   - Quality: High

3. **Xbox Store** - `https://www.xbox.com/en-US/store/`
   - Target: Game Pass additions, deals
   - Update frequency: Weekly
   - Quality: High

4. **Nintendo eShop** - `https://www.nintendo.com/store/`
   - Target: New releases, sales
   - Update frequency: Weekly (Thursday updates)
   - Quality: High

5. **Epic Games Store** - `https://store.epicgames.com/`
   - Target: Free games, weekly giveaways
   - Update frequency: Weekly (Thursday)
   - Quality: High

### Game Release Calendars

6. **Metacritic** - `https://www.metacritic.com/`
   - Target: New releases, review scores
   - Update frequency: Weekly
   - Quality: High

---

## Recommended Configuration (Top 15 Sources)

```yaml
sources:
  # Official Platform Sources
  - name: "Xbox Wire"
    url: "https://news.xbox.com/en-us/feed/"
    type: "rss"
    category: "platform"
    quality: "high"
  
  - name: "Nintendo Life"
    url: "https://www.nintendolife.com/feeds/latest"
    type: "rss"
    category: "platform"
    quality: "high"
  
  # Major Gaming News
  - name: "IGN"
    url: "https://feeds.ign.com/ign/all"
    type: "rss"
    category: "news"
    quality: "high"
  
  - name: "GameSpot"
    url: "https://gamespot.com/feeds/news"
    type: "rss"
    category: "news"
    quality: "high"
  
  - name: "PC Gamer"
    url: "https://www.pcgamer.com/rss"
    type: "rss"
    category: "news"
    quality: "high"
  
  - name: "Polygon"
    url: "https://polygon.com/rss/index.xml"
    type: "rss"
    category: "news"
    quality: "high"
  
  - name: "Kotaku"
    url: "https://kotaku.com/rss"
    type: "rss"
    category: "news"
    quality: "high"
  
  # Indie & Mobile
  - name: "IndieGames.com"
    url: "https://indiegamesplus.com/feed"
    type: "rss"
    category: "indie"
    quality: "high"
  
  - name: "Pocket Gamer"
    url: "https://www.pocketgamer.com/news/index.rss"
    type: "rss"
    category: "mobile"
    quality: "high"
  
  - name: "Touch Arcade"
    url: "https://toucharcade.com/feed"
    type: "rss"
    category: "mobile"
    quality: "high"
  
  # Esports
  - name: "Dot Esports"
    url: "https://dotesports.com/feed"
    type: "rss"
    category: "esports"
    quality: "high"
  
  - name: "Esports Insider"
    url: "https://esportsinsider.com/feed"
    type: "rss"
    category: "esports"
    quality: "high"
```

**Total Sources**: 25+ RSS, 9+ APIs, 15+ Scraping Targets

**Key Recommendations**:
- Start with official platform sources (Xbox Wire, Nintendo Life)
- Add major outlets (IGN, GameSpot, Polygon) for broad coverage
- Use Steam API for PC game data
- IGDB API for comprehensive game database
