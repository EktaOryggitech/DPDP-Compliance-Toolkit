import { Fragment, useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { Dialog, Transition } from '@headlessui/react'
import {
  Bars3Icon,
  XMarkIcon,
  HomeIcon,
  ComputerDesktopIcon,
  DocumentMagnifyingGlassIcon,
  CalendarIcon,
  DocumentChartBarIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline'
import clsx from 'clsx'
import { useAuthStore } from '../stores/authStore'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Applications', href: '/applications', icon: ComputerDesktopIcon },
  { name: 'Scans', href: '/scans', icon: DocumentMagnifyingGlassIcon },
  { name: 'Schedules', href: '/schedules', icon: CalendarIcon },
  { name: 'Reports', href: '/reports', icon: DocumentChartBarIcon },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const { user, logout } = useAuthStore()

  return (
    <>
      <div>
        {/* Mobile sidebar */}
        <Transition.Root show={sidebarOpen} as={Fragment}>
          <Dialog as="div" className="relative z-50 lg:hidden" onClose={setSidebarOpen}>
            <Transition.Child
              as={Fragment}
              enter="transition-opacity ease-linear duration-300"
              enterFrom="opacity-0"
              enterTo="opacity-100"
              leave="transition-opacity ease-linear duration-300"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <div className="fixed inset-0 bg-gray-900/80" />
            </Transition.Child>

            <div className="fixed inset-0 flex">
              <Transition.Child
                as={Fragment}
                enter="transition ease-in-out duration-300 transform"
                enterFrom="-translate-x-full"
                enterTo="translate-x-0"
                leave="transition ease-in-out duration-300 transform"
                leaveFrom="translate-x-0"
                leaveTo="-translate-x-full"
              >
                <Dialog.Panel className="relative mr-16 flex w-full max-w-xs flex-1">
                  <Transition.Child
                    as={Fragment}
                    enter="ease-in-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in-out duration-300"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                  >
                    <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                      <button
                        type="button"
                        className="-m-2.5 p-2.5"
                        onClick={() => setSidebarOpen(false)}
                      >
                        <span className="sr-only">Close sidebar</span>
                        <XMarkIcon className="h-6 w-6 text-white" aria-hidden="true" />
                      </button>
                    </div>
                  </Transition.Child>

                  <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-primary-700 px-6 pb-4">
                    <div className="flex h-16 shrink-0 items-center">
                      <span className="text-xl font-bold text-white">DPDP Scanner</span>
                    </div>
                    <nav className="flex flex-1 flex-col">
                      <ul role="list" className="flex flex-1 flex-col gap-y-7">
                        <li>
                          <ul role="list" className="-mx-2 space-y-1">
                            {navigation.map((item) => (
                              <li key={item.name}>
                                <Link
                                  to={item.href}
                                  className={clsx(
                                    location.pathname === item.href
                                      ? 'bg-primary-800 text-white'
                                      : 'text-primary-200 hover:text-white hover:bg-primary-800',
                                    'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold'
                                  )}
                                  onClick={() => setSidebarOpen(false)}
                                >
                                  <item.icon
                                    className={clsx(
                                      location.pathname === item.href
                                        ? 'text-white'
                                        : 'text-primary-200 group-hover:text-white',
                                      'h-6 w-6 shrink-0'
                                    )}
                                    aria-hidden="true"
                                  />
                                  {item.name}
                                </Link>
                              </li>
                            ))}
                          </ul>
                        </li>
                      </ul>
                    </nav>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </Dialog>
        </Transition.Root>

        {/* Desktop sidebar */}
        <div className="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-72 lg:flex-col">
          <div className="flex grow flex-col gap-y-5 overflow-y-auto bg-primary-700 px-6 pb-4">
            <div className="flex h-16 shrink-0 items-center">
              <span className="text-xl font-bold text-white">DPDP Scanner</span>
            </div>
            <nav className="flex flex-1 flex-col">
              <ul role="list" className="flex flex-1 flex-col gap-y-7">
                <li>
                  <ul role="list" className="-mx-2 space-y-1">
                    {navigation.map((item) => (
                      <li key={item.name}>
                        <Link
                          to={item.href}
                          className={clsx(
                            location.pathname === item.href
                              ? 'bg-primary-800 text-white'
                              : 'text-primary-200 hover:text-white hover:bg-primary-800',
                            'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold'
                          )}
                        >
                          <item.icon
                            className={clsx(
                              location.pathname === item.href
                                ? 'text-white'
                                : 'text-primary-200 group-hover:text-white',
                              'h-6 w-6 shrink-0'
                            )}
                            aria-hidden="true"
                          />
                          {item.name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </li>

                <li className="mt-auto">
                  <div className="flex items-center gap-x-4 px-2 py-3 text-sm text-primary-200">
                    <div className="flex-1">
                      <p className="font-medium text-white">{user?.full_name}</p>
                      <p className="text-xs text-primary-300">{user?.email}</p>
                    </div>
                    <button
                      onClick={logout}
                      className="p-2 rounded-md hover:bg-primary-800"
                      title="Logout"
                    >
                      <ArrowRightOnRectangleIcon className="h-5 w-5" />
                    </button>
                  </div>
                </li>
              </ul>
            </nav>
          </div>
        </div>

        {/* Main content */}
        <div className="lg:pl-72">
          {/* Mobile header */}
          <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
            <button
              type="button"
              className="-m-2.5 p-2.5 text-gray-700 lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <span className="sr-only">Open sidebar</span>
              <Bars3Icon className="h-6 w-6" aria-hidden="true" />
            </button>

            <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
              <div className="flex flex-1 items-center">
                <h1 className="text-lg font-semibold text-gray-900">
                  DPDP GUI Compliance Scanner
                </h1>
              </div>
            </div>
          </div>

          <main className="py-8">
            <div className="px-4 sm:px-6 lg:px-8">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </>
  )
}
