from playwright.sync_api import sync_playwright, expect

def test_create_game_button_opens_game():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto("http://localhost:5000/")

        # Fill name and hit "Create"
        page.fill("#name", "PlayAlice")
        page.click('button:has-text("Create")')

        # Wait for game UI to show up
        page.wait_for_selector("#game", state="visible")
        assert page.is_visible("#game")
        assert "Game Code:" in page.inner_text("#codeDisplay")
        assert "Round:" in page.inner_text("#roundDisplay")
        browser.close()

def test_two_players_join():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page1 = browser.new_page()
        page2 = browser.new_page()
        page1.goto("http://localhost:5000/")
        page2.goto("http://localhost:5000/")

        # Player 1 creates a game
        page1.fill("#name", "P1")
        page1.click('button:has-text("Create")')
        page1.wait_for_selector("#game", state="visible")
        game_code = page1.inner_text("#codeDisplay").split(":")[1].strip()

        # Player 2 joins using same code
        page2.fill("#name", "P2")
        page2.fill("#code", game_code)
        page2.click('button:has-text("Join")')
        page2.wait_for_selector("#game", state="visible")

        # Check both players see both names
        assert "P1" in page1.inner_text("#players")
        assert "P2" in page2.inner_text("#players")
        browser.close()

def test_game_turn_flow():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page1 = browser.new_page()
        page1.goto("http://localhost:5000/")
        page1.fill("#name", "TestPlayer")
        page1.click('button:has-text("Create")')
        page1.wait_for_selector("#game", state="visible")

        # Start the game
        page1.click("#startBtn")
        # Check controls are now enabled (player's turn)
        hit_btn = page1.locator('button:has-text("Hit")')
        stay_btn = page1.locator('button:has-text("Stay")')

        expect(hit_btn).to_be_enabled()
        expect(stay_btn).to_be_enabled()

        # Click Hit and check that a card appears
        page1.click('button:has-text("Hit")')
        page1.wait_for_selector(".card")
        expect(page1.locator(".card")).to_have_count(1)

        browser.close()