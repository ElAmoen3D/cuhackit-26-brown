<template>
  <a 
    :href="to" 
    class="sidebar-link"
    @click.prevent="$emit('click')"
  >
    <component :is="icon" :size="20" class="link-icon" />
    <span class="link-text">
      <slot></slot>
    </span>
  </a>
</template>

<script setup lang="ts">
interface Props {
  to?: string
  icon?: any
}

withDefaults(defineProps<Props>(), {
  to: '#',
})

defineEmits<{
  click: []
}>()
</script>

<style scoped>
.sidebar-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  color: #E1E8ED;
  text-decoration: none;
  border-radius: 6px;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  border: 1px solid transparent;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
}

.sidebar-link:hover {
  background: rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.3);
  color: #818CF8;
}

.sidebar-link:active {
  transform: scale(0.98);
}

.link-icon {
  flex-shrink: 0;
  color: inherit;
  transition: all 0.3s ease;
}

.link-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity 0.3s ease;
}
</style>
