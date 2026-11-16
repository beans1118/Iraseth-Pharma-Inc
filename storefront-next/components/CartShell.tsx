'use client';
import {CartProvider} from './CartProvider';
import CartDrawer from './CartDrawer';
import FloatingActions from './FloatingActions';
import type {ReactNode} from 'react';
export default function CartShell({children}:{children:ReactNode}){return <CartProvider>{children}<FloatingActions/><CartDrawer/></CartProvider>}
