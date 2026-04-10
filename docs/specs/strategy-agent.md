# Strategy Agent — Spec

## Purpose
Runs once per creator. Ingests all available data, classifies the niche, researches newsletter competitors, asks questions it cannot answer from research alone, and produces a strategy brief for human review. Does not fill gaps it cannot confirm — surfaces them and asks.

## Architecture decisions
- CLI-based, streaming output, inline pauses for operator input
- Step-based state machine with session persistence in `.agent/<creator-slug>/session.json`
- Three research skills run as Claude subagents (public_research, newsletter_research, trend_research)
- Output: `briefs/<creator-slug>/strategy-brief.md` (operator-facing) + `.agent/<creator-slug>/strategy-brief.json` (canonical, used by downstream agents)
- Unlimited revision loop in Step 6; learnings persisted to `.agent/<creator-slug>/learnings.json` and applied to all relevant fields on each round

---

## Step 0 — Data ingestion
**Skill:** `skills/public_research.py`

Takes stock of everything available before doing anything else.

Inputs in priority order:
1. Creator content URLs (social, YouTube, podcast, website)
2. Audience survey data if available
3. Audience feedback (testimonials, comments, DMs, product reviews)
4. Human-supplied context: engagement rate, growth signals, purchasing power indicators, products sold or affiliated with

Does not halt if data is thin. Flags what is missing and proceeds. Every gap surfaces in the output with an explicit note rather than an assumed answer.

---

## Step 1 — Niche classification
**Skill:** `skills/public_research.py`

### Stage 1a — Category classification
Assigns the creator to one primary category. If content spans more than one category at meaningful depth, surfaces the overlap and asks the operator to clarify before classifying.

| Category | What it covers | Revenue examples |
|---|---|---|
| Jobs | Skills, tools, software, career | The Rundown AI, Miss Excel, Industry Dive |
| Hobbies | Interest-led communities | The Dink, Unpolished Watch |
| Investments | Stocks, crypto, alternatives, business buying | MarketBeat, Codie Sanchez, Alts.co |
| Personal transformation | Weight loss, muscle gain, mindset, dating, health, healing | Sahil Bloom, Dan Go |

### Stage 1b — Sub-niche mapping
Maps all plausible sub-niches from the creator's content. Does not select. Lists what it found and asks which to combine or prioritise.

### Stage 1c — Niche candidate
Once the operator reacts, merges the confirmed sub-niches into a niche candidate and passes it to Steps 2 and 3.

**Gate:** Pauses and waits for operator input before locking the niche candidate.

---

## Step 2 — Newsletter competitor research
**Skill:** `skills/newsletter_research.py`

Scope: newsletters only. Includes individual creator newsletters, company/brand newsletters, media newsletters, and any regular editorial publication serving the same reader — regardless of platform (Substack, Beehiiv, Kit, Ghost, proprietary ESP). Does not include YouTube channels, podcasts, Reddit, or social media.

### What the agent does
- Searches for active newsletters in the niche using broad and specific queries
- Maps each against: approximate subscriber size (if available), positioning frame, content format, monetisation model
- Reads a sample of recent content from each where accessible
- Identifies: topics covered, angles taken, what they consistently miss, what reader responses reveal about unmet needs

### What it produces
- **Competitor brief:** one short paragraph per significant newsletter
- **Gap analysis:** what is not being covered, which reader needs are unmet, what positioning frames are unclaimed

### Niche depth recommendation
Does not apply a fixed re-niching rule. Lets the research determine the recommendation. If the newsletter landscape is genuinely uncrowded, recommends staying broad. If competition is dense, recommends going deeper and surfaces specific directions.

---

## Step 3 — Niche validation and filtering
**Skill:** `skills/trend_research.py`

Runs three filters. Where it cannot confirm a filter from available data, says so explicitly and asks rather than assuming.

### Filter 1 — Low competition
Evaluated using the competitor brief from Step 2. Can this creator realistically be a top-three newsletter in this vertical? Names the specific frame the creator could own. Flags if unclear.

### Filter 2 — High purchasing power
Confirmed if at least two of the following signals are present:
- Creator has successfully affiliated with or sponsored products above a meaningful price point, with audience response to confirm
- Creator's audience has responded to paid offers (product sales, paid community, course purchases)
- Survey data indicates disposable income or premium purchase behaviour
- The niche itself implies above-average spend

**Gate:** If fewer than two signals are present, the agent stops and states: "I cannot confirm purchasing power from the available data. Here is what I found and what I was unable to find. Please supply additional context before I proceed."

### Filter 3 — Easily identifiable audience
For creators with an existing following the default is yes. Checks growth signals and engagement rate where publicly available. Notes the gap and asks for human input where data is not accessible.

### Trend validation
Checks search volume trajectory, cultural or regulatory tailwinds, and consumer behaviour signals relevant to the niche. Assesses timing, not just existence. Flags signals that suggest saturation or declining interest.

---

## Step 4 — Creator intake questions
Before the synthesis pass, surfaces any questions that research alone cannot answer. Does not proceed to synthesis until always-ask questions are resolved.

### Always-ask (blocks synthesis until answered)
1. What is the specific moment or experience that led this creator to this topic? Not the polished version. The real one.
2. What does this creator believe that most people in this space get wrong?
3. What has this creator done, experienced, or built that gives them credibility here that is not obvious from their public content?
4. Who is the single most specific reader this newsletter is for? If you had to picture one person, who are they and what are they struggling with right now?

### Gap-specific (surfaced but operator can proceed without them)
- If purchasing power was unconfirmed: what products has this creator's audience bought, at what price point, and how did they respond?
- If archetype was ambiguous: how does this creator think of themselves — practitioner, learner, experimenter, or curator?
- If niche candidate was unclear: which sub-niche does the creator feel most strongly about and why?

---

## Step 5 — Synthesis pass
Takes everything from Steps 0–4 and fills the strategy brief in one pass. Where a gap remains unresolved, leaves the field blank with a note.

### Strategy brief fields

**Newsletter name**
Three name directions with one-line rationale each. Does not pick. Operator reacts and selects or redirects.

**Niche umbrella**
Confirmed niche position: category + confirmed sub-niche combination + one-sentence rationale for niche depth, grounded in competitor research findings.

**Target reader**
One paragraph. A specific person in a specific situation with a specific problem. Drawn from Step 4 intake answers.

**Newsletter statement**
`This newsletter helps [audience] achieve [dream outcome] by [unique mechanism or perspective].`

After producing this statement, runs a differentiation check: searches for existing newsletters with a similar statement and flags close matches. If not distinctive enough to be ownable, surfaces this and asks for a revision before proceeding.

**Why does this content need to exist?**
Two to three sentences. Drawn from trend data and gap analysis. Quantified where possible. This is the market timing argument.

**Why this creator specifically?**
Two to three sentences. Drawn directly from Step 4 intake answers. Named lived experience, contrarian belief, or earned credibility. No generalisations. Left blank with a note if intake answers did not resolve this.

**Top 3 content pillars**
Derived from creator's existing content format, reader's dream outcome, and gap analysis from Step 2. Each pillar names what the reader gets and how it moves them toward the newsletter statement.

**Creator archetype**
Primary archetype. Secondary as modifier if applicable. One sentence of evidence from creator content or intake answers.

| Archetype | What it looks like |
|---|---|
| Expert | Teaches from authority and earned experience |
| Student | Documents learning in real time |
| Experimenter | Tests things and reports results |
| Tastemaker | Curates and contextualises — value from selection and framing |

**Primary business model**
One selection. Derived from archetype and subscriber threshold:
- Under 5k: affiliates only
- 5k–20k: affiliates + sponsorships
- 20k+: coaching or digital products primary, sponsorships secondary

**Competitor insight**
One paragraph. Names the competitive landscape, the most significant newsletters in the space, and the specific white space this newsletter can own. Drawn directly from Step 2.

**One comparable newsletter**
One newsletter close but not identical to the proposed positioning. Agent suggests one from research. Operator confirms or replaces.

---

## Step 6 — Human review loop
Operator reviews the completed brief. Reacts to name directions, confirms or adjusts the niche, pushes back on ICP or positioning, corrects the archetype. Agent refines based on feedback.

- **Loop:** Unlimited rounds until operator explicitly locks the brief
- **Learnings:** Each round's feedback is stored to `.agent/<creator-slug>/learnings.json` and applied to all relevant fields before the next round
- **Lock trigger:** Operator says "lock it" or equivalent confirmation

---

## Output files
| File | Purpose |
|---|---|
| `briefs/<creator-slug>/strategy-brief.md` | Operator-facing. Only file the operator needs to read. |
| `.agent/<creator-slug>/strategy-brief.json` | Canonical. Read by all downstream agents. |
| `.agent/<creator-slug>/session.json` | Step state and outputs. Enables resume if interrupted. |
| `.agent/<creator-slug>/learnings.json` | Accumulated revision feedback across all review rounds. |
