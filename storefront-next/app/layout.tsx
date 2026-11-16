import type { Metadata } from 'next';
import SiteHeader from '@/components/SiteHeader';
import SiteFooter from '@/components/SiteFooter';
import CartShell from '@/components/CartShell';
import './globals.css';
export const metadata: Metadata = {title:{default:'Iraseth Pharma | Healthcare Solutions',template:'%s | Iraseth Pharma'},description:'Iraseth Pharma Incorporated provides integrated medical and diagnostic solutions for healthcare facilities in the Philippines.'};
export default function RootLayout({children,modal}:{children:React.ReactNode;modal:React.ReactNode}){return <html lang="en"><body><CartShell><SiteHeader/><main id="main-content">{children}</main><SiteFooter/>{modal}</CartShell></body></html>}
