<script lang="ts">
  import { mediaDevices, mediaStreamActions } from '$lib/mediaStream';
  import Screen from '$lib/icons/screen.svelte';
  import { onMount } from 'svelte';

  let deviceId: string = '';

  onMount(() => {
    // Pick first real camera (NDI devices already filtered out in enumerateDevices)
    if ($mediaDevices.length > 0) {
      deviceId = $mediaDevices[0].deviceId;
    }
  });

  // Keep deviceId in sync if mediaDevices list changes
  $: if ($mediaDevices.length > 0 && !deviceId) {
    deviceId = $mediaDevices[0].deviceId;
  }
</script>

<div class="flex items-center justify-center gap-1 text-xs">
  <button
    title="Share your screen"
    class="my-1 flex cursor-pointer gap-1 rounded-md border border-gray-400 bg-gray-800 bg-opacity-80 p-1 font-medium text-white hover:bg-gray-700"
    on:click={() => mediaStreamActions.startScreenCapture()}
  >
    <span>Share</span>
    <Screen classList={''} />
  </button>
  {#if $mediaDevices && $mediaDevices.length > 0}
    <select
      bind:value={deviceId}
      on:change={() => mediaStreamActions.switchCamera(deviceId)}
      id="devices-list"
      class="block cursor-pointer rounded-md border border-gray-400 bg-gray-800 bg-opacity-90 p-1 font-medium text-white"
      style="max-width: 200px; color: white; background-color: rgba(30,30,30,0.92);"
    >
      {#each $mediaDevices as device}
        <option value={device.deviceId} style="background:#1e1e1e; color:white;">
          {device.label || 'Camera ' + device.deviceId.substring(0, 6)}
        </option>
      {/each}
    </select>
  {:else}
    <span class="rounded-md bg-gray-800 bg-opacity-80 p-1 text-gray-300">No cameras found</span>
  {/if}
</div>
