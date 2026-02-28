<template>
  <div class="sidebar-body">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.sidebar-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
  flex: 1;
  overflow-y: auto;
}
</style>
