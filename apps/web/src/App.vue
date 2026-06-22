<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { api } from "./api";
import Laundry from "./Laundry.vue";
import Login from "./Login.vue";

type SessionStatus = "loading" | "authenticated" | "anonymous";

const session = ref<SessionStatus>("loading");

let unsubscribe: (() => void) | undefined;

onMounted(() => {
    unsubscribe = api.auth.subscribe((authenticated) => {
        session.value = authenticated ? "authenticated" : "anonymous";
    });

    api.auth
        .restore()
        .then((restored) => {
            session.value = restored ? "authenticated" : "anonymous";
        })
        .catch(() => {
            session.value = "anonymous";
        });
});

onUnmounted(() => {
    unsubscribe?.();
});
</script>

<template>
    <main v-if="session === 'loading'">
        <p>Loading...</p>
    </main>
    <Laundry v-else-if="session === 'authenticated'" />
    <Login v-else />
</template>
