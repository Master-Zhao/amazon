<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">AMAZON ADS OPTIMIZER</p>
        <h1>基础工程运行框架</h1>
      </div>
      <span class="phase-badge">Phase 1</span>
    </header>

    <nav class="nav" aria-label="基础导航">
      <RouterLink to="/">工程状态</RouterLink>
      <RouterLink to="/diagnostics/health">运行诊断</RouterLink>
      <a href="/api/docs/" target="_blank" rel="noreferrer">OpenAPI</a>
    </nav>

    <main class="content">
      <slot />
    </main>
  </div>
</template>
