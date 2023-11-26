<!-- eslint-disable vue/multi-word-component-names -->
<template>
  <div className="navbar  flex justify-between bg-base-100  z-10 shadow-md ">
    <div class="">
      <label
        htmlFor="left-sidebar-drawer"
        className="btn btn-primary drawer-button lg:hidden"
      >
        <Bars3Icon class="h-5 inline-block w-5"
      /></label>
      <h1 class="text-2xl font-semibold ml-2">{pageTitle}</h1>
    </div>

    <div className="order-last">
      <select className="select select-sm mr-4" data-choose-theme>
        <option disabled selected>Theme</option>
        <option value="light">Default</option>
        <option value="dark">Dark</option>
        <option value="corporate">Corporate</option>
        <option value="retro">Retro</option>
      </select>
      <label className="swap ">
        <input type="checkbox" />
        <SunIcon
          data-set-theme="light"
          data-act-class="ACTIVECLASS"
          class="fill-current w-6 h-6 ${currentTheme === 'dark' ? 'swap-on' : 'swap-off'}"
        />
        <MoonIcon
          data-set-theme="dark"
          data-act-class="ACTIVECLASS"
          :class="
            'fill-current w-6 h-6' + currentTheme === 'light'
              ? 'swap-on'
              : 'swap-off'
          "
        />
      </label>

      <button
        className="btn btn-ghost ml-4  btn-circle"
        :on-click="openNotification"
      >
        <div className="indicator">
          <BellIcon class="h-6 w-6" />
          {noOfNotifications > 0 ?
          <span className="indicator-item badge badge-secondary badge-sm"
            >{noOfNotifications}</span
          >
          : null }
        </div>
      </button>

      <div className="dropdown dropdown-end ml-4">
        <label :tabIndex="0" className="btn btn-ghost btn-circle avatar">
          <div className="w-10 rounded-full">
            <img src="https://placeimg.com/80/80/people" alt="profile" />
          </div>
        </label>
        <ul
          :tabIndex="0"
          className="menu menu-compact dropdown-content mt-3 p-2 shadow bg-base-100 rounded-box w-52"
        >
          <li className="justify-between">
            <NuxtLink to="/app/settings-profile">
              Profile Settings
              <span className="badge">New</span>
            </NuxtLink>
          </li>
          <li className="">
            <NuxtLink to="/app/settings-billing">Bill History</NuxtLink>
          </li>
          <div className="divider mt-0 mb-0"></div>
          <li><a :on-click="logoutUser">Logout</a></li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { Ref } from 'vue'

const currentTheme = Ref('')
const logoutUser = (event: MouseEvent): void => {
  console.log(event)
}
const openNotification = (event: any) => {
  console.log(event)
}
</script>
