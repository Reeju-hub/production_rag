import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Supabase Admin Client
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get('code');

  if (!code) {
    return NextResponse.json({ error: 'Authorization code missing from Slack' }, { status: 400 });
  }

  try {
    // 1. Exchange authorization code for Slack Bot Token
    const tokenResponse = await fetch('https://slack.com/api/oauth.v2.access', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: process.env.NEXT_PUBLIC_SLACK_CLIENT_ID!,
        client_secret: process.env.SLACK_CLIENT_SECRET!,
        code: code,
        redirect_uri: `${process.env.NEXT_PUBLIC_APP_URL}/api/auth/slack/callback`,
      }),
    });

    const data = await tokenResponse.json();

    if (!data.ok) {
      return NextResponse.json({ error: data.error || 'Failed to exchange Slack token' }, { status: 400 });
    }

    const { team, access_token, bot_user_id } = data;

    // 2. Save or update installation inside Supabase database
    const { error: dbError } = await supabase
      .from('slack_installations')
      .upsert({
        team_id: team.id,
        team_name: team.name,
        access_token: access_token,
        bot_user_id: bot_user_id,
        updated_at: new Date().toISOString(),
      }, { onConflict: 'team_id' });

    if (dbError) {
      console.error('Database Error:', dbError);
      return NextResponse.json({ error: 'Failed to save installation to database' }, { status: 500 });
    }

    // 3. Redirect user back to dashboard or success page
    return NextResponse.redirect(`${process.env.NEXT_PUBLIC_APP_URL}/dashboard?success=true`);

  } catch (err) {
    console.error('OAuth Exception:', err);
    return NextResponse.json({ error: 'Internal Server Error during Slack OAuth' }, { status: 500 });
  }
}