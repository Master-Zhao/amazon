<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/features/auth/stores/auth'
import { useTenantContextStore } from '@/features/tenant-context/stores/tenantContext'

const authStore = useAuthStore()
const tenantContextStore = useTenantContextStore()
const router = useRouter()
const showMenu = ref(false)
const isHovering = ref(false)
const loggingOut = ref(false)
const menuRef = ref<HTMLElement | null>(null)

const userInitial = ref('')

function updateUserInfo() {
  if (authStore.currentUser) {
    const name = authStore.currentUser.username || authStore.currentUser.email
    userInitial.value = name.charAt(0).toUpperCase()
  }
}
updateUserInfo()

function handleMouseEnter() {
  isHovering.value = true
}

function handleMouseLeave() {
  isHovering.value = false
}

function toggleMenu() {
  showMenu.value = !showMenu.value
}

function handleClickOutside(event: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(event.target as Node)) {
    showMenu.value = false
  }
}

async function performLogout() {
  loggingOut.value = true
  try {
    await authStore.logout()
    tenantContextStore.clear()
    await router.replace({ name: 'login' })
  } finally {
    loggingOut.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="menuRef" class="user-avatar-menu">
    <button
      class="avatar-button"
      :class="{ 'avatar-hover': isHovering, 'avatar-active': showMenu }"
      type="button"
      aria-label="用户菜单"
      aria-haspopup="true"
      :aria-expanded="showMenu"
      @mouseenter="handleMouseEnter"
      @mouseleave="handleMouseLeave"
      @click="toggleMenu"
    >
      <span class="avatar-ring">
        <span class="avatar-initial">{{ userInitial }}</span>
      </span>
      <span v-if="isHovering || showMenu" class="avatar-hint">▼</span>
    </button>

    <Transition name="dropdown">
      <div v-if="showMenu" class="avatar-dropdown">
        <div class="dropdown-footer">
          <button
            class="dropdown-logout-btn"
            type="button"
            :disabled="loggingOut"
            @click="performLogout"
          >
            <span class="logout-icon">⏻</span>
            <span>{{ loggingOut ? '正在退出…' : '退出登录' }}</span>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.user-avatar-menu {
  position: relative;
  z-index: 200;
}

.avatar-button {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  border: none;
  border-radius: 999px;
  padding: 0;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.avatar-ring {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 50%;
  border: 2px solid rgba(234, 240, 236, 0.35);
  background: linear-gradient(135deg, #bd5c30 0%, #e8844a 100%);
  transition: all 0.25s ease;
  box-shadow: 0 0 0 0 rgba(189, 92, 48, 0);
}

.avatar-hover .avatar-ring,
.avatar-active .avatar-ring {
  border-color: rgba(234, 240, 236, 0.7);
  box-shadow: 0 0 0 3px rgba(189, 92, 48, 0.3);
  transform: scale(1.08);
}

.avatar-initial {
  color: #fff;
  font-weight: 700;
  font-size: 0.85rem;
  line-height: 1;
  user-select: none;
}

.avatar-hint {
  color: rgba(234, 240, 236, 0.7);
  font-size: 0.55rem;
  transition: transform 0.2s ease;
}

.avatar-active .avatar-hint {
  transform: rotate(180deg);
}

.avatar-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: -0.5rem;
  width: 160px;
  border-radius: 0.75rem;
  padding: 0;
  background: #fff;
  color: #18211d;
  box-shadow:
    0 4px 6px -1px rgba(42, 48, 44, 0.08),
    0 10px 40px -4px rgba(42, 48, 44, 0.15),
    0 0 0 1px rgba(38, 63, 53, 0.08);
  overflow: hidden;
}

.dropdown-enter-active {
  transition: all 0.2s ease-out;
}

.dropdown-leave-active {
  transition: all 0.15s ease-in;
}

.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-8px) scale(0.97);
}

.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.99);
}

.dropdown-footer {
  padding: 0.5rem;
}

.dropdown-logout-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  border: none;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  color: #8d3024;
  background: transparent;
  font: inherit;
  font-size: 0.84rem;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease;
}

.dropdown-logout-btn:hover {
  background: #ffe0dc;
}

.dropdown-logout-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}

.logout-icon {
  font-size: 0.95rem;
}
</style>
