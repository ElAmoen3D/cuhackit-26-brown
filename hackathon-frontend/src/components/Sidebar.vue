<template>
  <div class="sidebar-wrapper">
    <Teleport to="body" v-if="isMounted">
      <Transition name="sidebar-fade">
        <div
          v-if="isDesktop"
          class="desktop-sidebar"
          :class="{ 'sidebar-right': sidebarPosition === 'right' }"
          :style="{
            width: animate ? (open ? '300px' : '60px') : '300px',
          }"
          @mouseenter="open = true"
          @mouseleave="open = false"
        >
          <button 
            class="position-toggle-btn"
            @click="toggleSidebarPosition"
            title="Toggle sidebar position"
            :aria-label="sidebarPosition === 'left' ? 'Move sidebar to right' : 'Move sidebar to left'"
          >
            <ChevronLeft v-if="sidebarPosition === 'right'" :size="18" />
            <ChevronRight v-else :size="18" />
          </button>

          <slot></slot>
        </div>
      </Transition>
    </Teleport>

    <div class="mobile-sidebar-header" v-if="!isDesktop">
      <button
        class="mobile-menu-btn"
        @click="open = !open"
        :aria-label="open ? 'Close menu' : 'Open menu'"
      >
        <MenuIcon v-if="!open" :size="24" />
        <XIcon v-else :size="24" />
      </button>
    </div>

    <Teleport to="body" v-if="isMounted">
      <Transition name="mobile-slide">
        <div v-if="open && !isDesktop" class="mobile-sidebar-panel">
          <button class="mobile-close-btn" @click="open = false">
            <XIcon :size="24" />
          </button>
          <slot></slot>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, provide, Ref } from 'vue'
import { Menu as MenuIcon, X as XIcon, ChevronLeft, ChevronRight } from 'lucide-vue-next'

interface Props {
  animate?: boolean
  defaultOpen?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  animate: true,
  defaultOpen: false,
})

const open = ref(props.defaultOpen)
const isMounted = ref(false)
const isDesktop = ref(true)
const sidebarPosition = ref<'left' | 'right'>('left')

// Provide context
provide('sidebarOpen', open as Ref<boolean>)
provide('sidebarAnimate', ref(props.animate) as Ref<boolean>)

const toggleSidebarPosition = () => {
  sidebarPosition.value = sidebarPosition.value === 'left' ? 'right' : 'left'
  localStorage.setItem('sidebarPosition', sidebarPosition.value)
}

const checkScreenSize = () => {
  isDesktop.value = window.innerWidth >= 768
  if (isDesktop.value) {
    open.value = false
  }
}

onMounted(() => {
  isMounted.value = true
  const savedPosition = localStorage.getItem('sidebarPosition') as 'left' | 'right' | null
  if (savedPosition) {
    sidebarPosition.value = savedPosition
  }
  checkScreenSize()
  window.addEventListener('resize', checkScreenSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize)
})
</script>

<style scoped>
:root {
  --soc-midnight: var(--tiger-bg);
  --soc-midnight-light: var(--tiger-surface);
  --soc-midnight-lighter: var(--tiger-surface-border);
  --soc-indigo: var(--tiger-primary);
  --soc-indigo-bright: var(--tiger-secondary);
  --soc-text-primary: var(--tiger-text-base);
  --soc-border: var(--tiger-surface-border);
}

.desktop-sidebar {
  position: fixed;
  left: 0;
  top: 0;
  height: 100vh;
  background: var(--tiger-surface);
  border-right: 1px solid var(--tiger-surface-border);
  box-shadow: 4px 0 15px rgba(0, 0, 0, 0.03);
  overflow-y: auto;
  transition: width 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), left 0.4s ease, right 0.4s ease;
  z-index: 10;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.desktop-sidebar.sidebar-right {
  left: auto;
  right: 0;
  border-right: none;
  border-left: 1px solid var(--tiger-surface-border);
  box-shadow: -4px 0 15px rgba(0, 0, 0, 0.03);
}

.position-toggle-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: #818CF8;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  width: 36px;
  height: 36px;
  z-index: 11;
}

.position-toggle-btn:hover {
  background: rgba(99, 102, 241, 0.2);
  border-color: rgba(99, 102, 241, 0.5);
  color: #E1E8ED;
  transform: scale(1.1);
}

.position-toggle-btn:active {
  transform: scale(0.95);
}

.mobile-sidebar-header {
  display: none;
  height: 60px;
  padding: 16px;
  background: linear-gradient(90deg, #161B22 0%, #21262D 100%);
  border-bottom: 1px solid #2D333B;
  align-items: center;
  justify-content: space-between;
}

.mobile-menu-btn {
  background: none;
  border: none;
  color: #E1E8ED;
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.mobile-menu-btn:hover {
  color: #818CF8;
}

.mobile-sidebar-panel {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  background: #0B0E14;
  z-index: 100;
  padding: 40px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.mobile-close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  background: none;
  border: none;
  color: #E1E8ED;
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  z-index: 50;
}

.mobile-close-btn:hover {
  color: #818CF8;
}

@media (max-width: 767px) {
  .mobile-sidebar-header {
    display: flex;
  }

  .desktop-sidebar {
    display: none;
  }
}

.sidebar-fade-enter-active,
.sidebar-fade-leave-active {
  transition: opacity 0.3s ease;
}

.sidebar-fade-enter-from,
.sidebar-fade-leave-to {
  opacity: 0;
}

.mobile-slide-enter-active,
.mobile-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.mobile-slide-enter-from,
.mobile-slide-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}
</style>