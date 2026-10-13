import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy" };
export default function Privacy() {
  return (<>
    <h1>Privacy</h1>
    <p><strong>This is an invite-only educational demo.</strong> This page summarises what happens to your information.</p>
    <h2>What we keep</h2>
    <ul>
      <li>If you sign in: your email address, used only to send sign-in links (handled by Supabase).</li>
      <li>If you save a scenario: its settings and results. Your purchases are saved only if you tick the box to save
        them, and merchant names are never saved.</li>
    </ul>
    <h2>What we don&rsquo;t keep</h2>
    <ul>
      <li>Uploaded CSV files are read to find your purchases and then discarded. They are never stored.</li>
      <li>Simulations you run without signing in are not stored.</li>
      <li>We don&rsquo;t use advertising or third-party trackers.</li>
    </ul>
    <h2>Deleting your data</h2>
    <p>You can delete any saved scenario at any time. To delete your account, contact the person who invited you.
      Saved scenarios are not backed up, so deleted data is gone straight away.</p>
    <p className="small muted">Plain-language summary for the demo; not reviewed by a lawyer (owner decision for an invite-only demo).</p>
  </>);
}
