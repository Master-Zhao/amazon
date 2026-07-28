<template>
  <section class="hero-card">
    <p class="eyebrow">FOUNDATION READY FOR VERIFICATION</p>
    <h2>这里只展示真实的基础工程状态</h2>
    <p>
      当前阶段提供 Django、Vue、Celery、MySQL、Redis、Nginx、OpenAPI
      与健康诊断基础。登录、Tenant、广告、报表和智能优化业务尚未实现。
    </p>
    <RouterLink class="primary-link" to="/diagnostics/health">
      检查服务依赖
    </RouterLink>
  </section>

  <section class="capability-grid" aria-label="Phase 1 能力边界">
    <article>
      <span>01</span>
      <h3>可验证平台</h3>
      <p>健康检查、requestId、统一错误、OpenAPI 和 Celery smoke。</p>
    </article>
    <article>
      <span>02</span>
      <h3>明确边界</h3>
      <p>不提供虚假登录、静态 Dashboard 或硬编码广告数据。</p>
    </article>
    <article>
      <span>03</span>
      <h3>后续入口</h3>
      <p>Phase 2 才会在授权后实现认证、多租户与数据权限。</p>
    </article>
  </section>
</template>
