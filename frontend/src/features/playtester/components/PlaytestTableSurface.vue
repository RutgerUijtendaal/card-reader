<template>
  <section class="playtester-table">
    <slot />
  </section>
</template>

<style scoped>
.playtester-table {
  --playtest-surface: color-mix(in srgb, var(--color-surface-soft) 78%, var(--app-bg-to) 22%);
  --playtest-surface-accent: color-mix(in srgb, var(--color-control-accent) 10%, transparent);
  --playtest-panel: color-mix(in srgb, var(--color-surface-strong) 88%, transparent);
  --playtest-panel-muted: color-mix(in srgb, var(--color-surface-muted) 82%, transparent);
  --playtest-panel-strong: color-mix(in srgb, var(--color-popover) 94%, transparent);
  --playtest-border: color-mix(in srgb, var(--color-border) 82%, transparent);
  --playtest-grid-line: color-mix(in srgb, var(--color-border) 42%, transparent);
  --playtest-text: var(--color-text);
  --playtest-text-muted: var(--color-text-muted);
  --playtest-text-soft: var(--color-text-soft);
  --playtest-shadow: 0 1.1rem 2.4rem rgba(15, 23, 42, 0.12);
  position: relative;
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background:
    radial-gradient(circle at 18% 0%, var(--playtest-surface-accent), transparent 28%),
    linear-gradient(var(--playtest-grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--playtest-grid-line) 1px, transparent 1px),
    var(--playtest-surface);
  background-size: auto, 1.35rem 1.35rem, 1.35rem 1.35rem, auto;
  color: var(--playtest-text);
  box-shadow: var(--playtest-shadow);
}

:global(html.dark) .playtester-table {
  --playtest-surface: #141817;
  --playtest-surface-accent: color-mix(in srgb, var(--color-control-accent) 15%, transparent);
  --playtest-panel: rgba(8, 10, 10, 0.76);
  --playtest-panel-muted: rgba(8, 10, 10, 0.64);
  --playtest-panel-strong: rgba(12, 15, 15, 0.93);
  --playtest-border: rgba(255, 255, 255, 0.08);
  --playtest-grid-line: rgba(255, 255, 255, 0.035);
  --playtest-text: rgba(255, 255, 255, 0.92);
  --playtest-text-muted: rgba(255, 255, 255, 0.82);
  --playtest-text-soft: rgba(255, 255, 255, 0.48);
  --playtest-shadow: 0 1.5rem 4rem rgba(0, 0, 0, 0.24);
}
</style>
