import { inject, provide, shallowRef, type InjectionKey, type Ref } from 'vue';

const scrollContainerKey: InjectionKey<Ref<HTMLElement | null>> = Symbol('scroll-container');

export const provideScrollContainer = (container: Ref<HTMLElement | null>): void => {
  provide(scrollContainerKey, container);
};

export const useScrollContainer = (): Ref<HTMLElement | null> =>
  inject(scrollContainerKey, shallowRef<HTMLElement | null>(null));
