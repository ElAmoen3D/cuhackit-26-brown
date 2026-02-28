<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  height: 100%;
  background: #0b0b0e;
}

#app {
  height: 100vh;
  overflow: hidden;
}
</style>