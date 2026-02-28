<template>
  <div id="app">
    <Sidebar />
    <div class="content">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
</script>

<style>
body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
}

#app {
  display: flex;
  height: 100vh;
}

.content {
  flex: 1;
  padding: 20px;
  background: #f5f6fa;
}
</style>