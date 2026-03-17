# Campaigns And Briefs

Campaigns are for goals that are bigger than one task and bigger than one run.

## Create a campaign

```bash
hive campaign create \
  --title "Launch week" \
  --goal "Ship the website and launch docs" \
  --project-id website \
  --project-id docs
```

## Tick the campaign

```bash
hive campaign tick <campaign-id>
```

That launches the next bounded set of runs for the campaign and updates the campaign record.

## Generate briefs

```bash
hive brief daily
hive brief weekly
```

Briefs are searchable artifacts. Use them as the morning view for a portfolio or as a handoff summary for another operator.

## When campaigns help

- release prep
- reliability cleanup across several projects
- recurring docs or content work
- overnight exploit/explore loops
