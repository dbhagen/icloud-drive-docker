<template>
  <div>
    <div className="drawer drawer-mobile">
      <input
        id="left-sidebar-drawer"
        type="checkbox"
        className="drawer-toggle"
      />
      <PageContent />
      <!-- <LeftSidebar /> -->
    </div>

    <!-- <RightSidebar /> -->

    <!-- <NotificationContainer /> -->

    <!-- <ModalLayout /> -->

    <AppHeader />
    <slot />
    <AppFooter />
  </div>
</template>
