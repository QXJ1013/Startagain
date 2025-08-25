<template>
    <div><Radar :data="chartData" :options="chartOptions" /></div>
  </template>
  
  <script setup lang="ts">
  import { computed } from "vue";
  import { Radar } from "vue-chartjs";
  import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from "chart.js";
  ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);
  
  const props = defineProps<{ dims: Array<{ pnm: string; score_0_7: number }> }>();
  
  const chartData = computed(() => ({
    labels: props.dims.map(d => d.pnm),
    datasets: [{
      label: "PNM (0-7)",
      data: props.dims.map(d => d.score_0_7),
      fill: true
    }]
  }));
  
  const chartOptions = {
    responsive: true,
    scales: { r: { suggestedMin: 0, suggestedMax: 7, ticks: { stepSize: 1 } } },
    plugins: { legend: { display: false } }
  };
  </script>
  