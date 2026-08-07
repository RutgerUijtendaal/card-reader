local CONFIG = {
    auto_sync_enabled = true,
    library_manifest_url = "https://maityscardgame.com/tts/card-library/cards.json",
    auto_sync_retry_delays = { 2, 5, 15, 30 },
    library_batch_spacing = 3,
    source_region_guids = {
        "cb7760",
    },
    spawn_position = { x = -45, y = 3, z = 50 },
    stack_y_spacing = 0.08,
    fuzzy_name_distance = 1,
    index_batch_size = 50,
    spawn_batch_size = 5,
    wait_timeout_seconds = 15,
    finalize_wait_frames = 210,
    finalize_search_radius = 3,
}

local library_sync_state = {
    generation = 0,
    in_progress = false,
}

function onLoad()
    if not CONFIG.auto_sync_enabled then
        return
    end

    Wait.frames(function()
        startCardReaderLibraryAutoSync()
    end, 1)
end

function startCardReaderLibraryAutoSync()
    if CONFIG.auto_sync_enabled then
        startCardReaderLibrarySync(true)
    end
end

function syncCardReaderLibrary()
    startCardReaderLibrarySync(false)
end

function importCardReaderDeck(encoded)
    local payload = decodePayload(encoded)
    validateDeckPayload(payload)

    startImportJob(payload, buildImportRequests(payload))
end

function importCardReaderCards(encoded)
    local payload = decodePayload(encoded)
    validateCardPayload(payload)
    spawnCardReaderSheetDeck(payload)
end

function startCardReaderLibrarySync(is_automatic)
    if is_automatic and not CONFIG.auto_sync_enabled then
        return
    end
    if library_sync_state.in_progress then
        print("A Card Reader library synchronization is already running.")
        return
    end
    if trim(CONFIG.library_manifest_url or "") == "" then
        print("Card Reader library synchronization is not configured: library_manifest_url is empty.")
        return
    end

    library_sync_state.generation = library_sync_state.generation + 1
    library_sync_state.in_progress = true
    local job = {
        generation = library_sync_state.generation,
        is_automatic = is_automatic,
        retry_index = 1,
    }
    print("Fetching the latest Card Reader library manifest.")
    requestCardReaderLibraryManifest(job)
end

function requestCardReaderLibraryManifest(job)
    if not librarySyncJobIsCurrent(job) then
        return
    end
    if job.is_automatic and not CONFIG.auto_sync_enabled then
        finishCardReaderLibrarySync(job)
        return
    end

    WebRequest.get(cardReaderLibraryRequestUrl(job), function(request)
        if not librarySyncJobIsCurrent(job) then
            return
        end
        if request.is_error then
            retryCardReaderLibrarySync(job, "request failed: " .. tostring(request.error), nil)
            return
        end

        local response_code = tonumber(request.response_code or 0) or 0
        if response_code == 304 then
            job.cache_bust = tostring(math.random(100000, 999999)) .. "-" .. tostring(job.retry_index)
            retryCardReaderLibrarySync(job, "received an empty cached response", nil)
            return
        end
        if response_code == 429 or response_code >= 500 then
            retryCardReaderLibrarySync(
                job,
                "server returned HTTP " .. tostring(response_code),
                request.getResponseHeader("Retry-After")
            )
            return
        end
        if response_code ~= 200 then
            failCardReaderLibrarySync(job, "server returned HTTP " .. tostring(response_code))
            return
        end

        local decoded_ok, payload = pcall(JSON.decode, request.text)
        if not decoded_ok then
            failCardReaderLibrarySync(job, "manifest JSON is invalid: " .. tostring(payload))
            return
        end
        local validation_ok, validation_error = pcall(validateCardPayload, payload)
        if not validation_ok then
            failCardReaderLibrarySync(job, "manifest validation failed: " .. tostring(validation_error))
            return
        end

        startCardReaderLibraryScan(job, payload)
    end)
end

function cardReaderLibraryRequestUrl(job)
    if job.cache_bust == nil then
        return CONFIG.library_manifest_url
    end
    local separator = string.find(CONFIG.library_manifest_url, "?", 1, true) and "&" or "?"
    return CONFIG.library_manifest_url
        .. separator
        .. "card_reader_refresh="
        .. tostring(job.cache_bust)
end

function retryCardReaderLibrarySync(job, reason, retry_after)
    local delay = CONFIG.auto_sync_retry_delays[job.retry_index]
    if delay == nil or (job.is_automatic and not CONFIG.auto_sync_enabled) then
        failCardReaderLibrarySync(job, reason .. "; retry limit reached")
        return
    end

    local requested_delay = tonumber(retry_after or 0) or 0
    if requested_delay > delay then
        delay = requested_delay
    end
    job.retry_index = job.retry_index + 1
    print(string.format("Card Reader library sync %s; retrying in %d seconds.", reason, delay))
    Wait.time(function()
        requestCardReaderLibraryManifest(job)
    end, delay)
end

function failCardReaderLibrarySync(job, reason)
    if not librarySyncJobIsCurrent(job) then
        return
    end
    print("Card Reader library synchronization stopped: " .. tostring(reason))
    finishCardReaderLibrarySync(job)
end

function finishCardReaderLibrarySync(job)
    if librarySyncJobIsCurrent(job) then
        library_sync_state.in_progress = false
    end
end

function librarySyncJobIsCurrent(job)
    return library_sync_state.in_progress and job.generation == library_sync_state.generation
end

function inspectCardReaderLibrary()
    local search_index = buildSearchIndex(CONFIG.source_region_guids)
    local rows = {}

    for _, entry in ipairs(search_index.entries) do
        table.insert(rows, entry.name or "-")
    end

    print(table.concat(rows, "\n"))
end

function decodePayload(encoded)
    local ok, json_text = pcall(base64Decode, encoded)
    if not ok then
        error("Failed to decode base64 payload: " .. tostring(json_text))
    end

    return JSON.decode(json_text)
end

function validateDeckPayload(payload)
    if type(payload) ~= "table" then
        error("Decoded payload must be a table.")
    end

    if payload.schema ~= "card-reader.tts-deck.v1" then
        error("Unsupported payload schema: " .. tostring(payload.schema))
    end

    if type(payload.deck) ~= "table" or type(payload.deck.name) ~= "string" then
        error("Payload deck metadata is invalid.")
    end

    if type(payload.cards) ~= "table" then
        error("Payload cards collection is invalid.")
    end
end

function validateCardPayload(payload)
    if type(payload) ~= "table" then
        error("Decoded payload must be a table.")
    end

    if payload.schema == "card-reader.tts-cards.v1" then
        error("This direct-card export is outdated. Re-export it from Card Reader to use sheet-based cards.")
    end

    if payload.schema ~= "card-reader.tts-cards.v2" then
        error("Unsupported payload schema: " .. tostring(payload.schema))
    end

    if type(payload.collection) ~= "table" or type(payload.collection.name) ~= "string" then
        error("Payload collection metadata is invalid.")
    end

    if type(payload.card_back_url) ~= "string" or trim(payload.card_back_url) == "" then
        error("Payload card back URL is invalid.")
    end

    if type(payload.sheets) ~= "table" or #payload.sheets == 0 then
        error("Payload sheets collection is invalid.")
    end

    if type(payload.cards) ~= "table" or #payload.cards == 0 then
        error("Payload cards collection is invalid.")
    end

    local sheets_by_id = {}
    for index, sheet in ipairs(payload.sheets) do
        if type(sheet) ~= "table" then
            error("Payload sheet entry " .. tostring(index) .. " is invalid.")
        end
        local columns = math.floor(tonumber(sheet.columns or 0) or 0)
        local rows = math.floor(tonumber(sheet.rows or 0) or 0)
        local sheet_id = trim(sheet.sheet_id or "")
        if sheet_id == ""
            or trim(sheet.face_url or "") == ""
            or columns <= 0
            or rows <= 0
            or columns > 10
            or rows > 7
            or sheets_by_id[sheet_id] ~= nil then
            error("Payload sheet entry " .. tostring(index) .. " is invalid.")
        end
        sheets_by_id[sheet_id] = sheet
    end

    for index, entry in ipairs(payload.cards) do
        if type(entry) ~= "table" then
            error("Payload card entry " .. tostring(index) .. " is invalid.")
        end
        local sheet = sheets_by_id[trim(entry.sheet_id or "")]
        local slot_index = math.floor(tonumber(entry.slot_index or -1) or -1)
        if trim(entry.card_id or "") == ""
            or trim(entry.card_version_id or "") == ""
            or trim(entry.name or "") == ""
            or sheet == nil
            or slot_index < 0
            or slot_index >= (tonumber(sheet.columns) * tonumber(sheet.rows))
            or math.floor(tonumber(entry.quantity or 0) or 0) <= 0 then
            error("Payload card entry " .. tostring(index) .. " is invalid.")
        end
    end

    if payload.skipped ~= nil and type(payload.skipped) ~= "table" then
        error("Payload skipped collection is invalid.")
    end
end

function spawnCardReaderSheetDeck(payload, options)
    options = options or {}
    local custom_deck = {}
    local sheet_keys = {}
    for index, sheet in ipairs(payload.sheets) do
        sheet_keys[sheet.sheet_id] = index
        custom_deck[index] = buildCustomDeckState(sheet, payload.card_back_url)
    end

    local contained = {}
    local deck_ids = {}
    for _, entry in ipairs(payload.cards) do
        local sheet_key = sheet_keys[entry.sheet_id]
        local card_id = (sheet_key * 100) + math.floor(tonumber(entry.slot_index))
        local quantity = math.floor(tonumber(entry.quantity))
        for _ = 1, quantity do
            table.insert(deck_ids, card_id)
            table.insert(contained, buildSheetCardData(
                entry,
                card_id,
                sheet_key,
                custom_deck[sheet_key],
                payload.sheets[sheet_key].face_url
            ))
        end
    end

    logMissingCards(buildExportSkippedRequests(payload.skipped))
    local object_data
    if #contained == 1 then
        object_data = contained[1]
    else
        object_data = buildSheetDeckData(payload.collection.name, deck_ids, custom_deck, contained)
    end

    spawnObjectData({
        data = object_data,
        position = options.position or CONFIG.spawn_position,
        callback_function = function(object)
            if object ~= nil and not object.isDestroyed() then
                if #contained > 1 then
                    object.setName(payload.collection.name)
                end
                print(string.format(
                    "Imported '%s' with %d cards across %d sheets.",
                    payload.collection.name,
                    #contained,
                    #payload.sheets
                ))
            end
            if type(options.callback_function) == "function" then
                options.callback_function(object, #contained)
            end
        end,
    })
end

function buildCustomDeckState(sheet, card_back_url)
    return {
        FaceURL = verifiedAssetUrl(trim(sheet.face_url)),
        BackURL = trim(card_back_url),
        NumWidth = math.floor(tonumber(sheet.columns)),
        NumHeight = math.floor(tonumber(sheet.rows)),
        BackIsHidden = true,
        UniqueBack = false,
    }
end

function buildSheetCardData(entry, card_id, sheet_key, custom_deck_state, sheet_url)
    local gm_notes = JSON.encode({
        schema = "card-reader.tts-card.v2",
        card_id = trim(entry.card_id),
        card_version_id = trim(entry.card_version_id),
        image_checksum = trim(entry.image_checksum or ""),
        sheet_id = trim(entry.sheet_id),
        slot_index = math.floor(tonumber(entry.slot_index)),
        stable_sheet_url = trim(sheet_url),
        lifecycle_status = trim(entry.lifecycle_status or ""),
    })
    return {
        Name = "CardCustom",
        Transform = defaultObjectTransform(),
        Nickname = trim(entry.name),
        Description = "",
        GMNotes = gm_notes,
        CardID = card_id,
        SidewaysCard = false,
        CustomDeck = {
            [sheet_key] = custom_deck_state,
        },
        LuaScript = "",
        LuaScriptState = "",
        XmlUI = "",
    }
end

function buildSheetDeckData(name, deck_ids, custom_deck, contained)
    return {
        Name = "DeckCustom",
        Transform = defaultObjectTransform(),
        Nickname = name,
        Description = "",
        GMNotes = "",
        DeckIDs = deck_ids,
        CustomDeck = custom_deck,
        ContainedObjects = contained,
        LuaScript = "",
        LuaScriptState = "",
        XmlUI = "",
    }
end

function defaultObjectTransform()
    return {
        posX = 0,
        posY = 0,
        posZ = 0,
        rotX = 0,
        rotY = 180,
        rotZ = 180,
        scaleX = 1,
        scaleY = 1,
        scaleZ = 1,
    }
end

function buildImportRequests(payload)
    local requests = {}

    if type(payload.hero) == "table" and tonumber(payload.hero.quantity or 0) > 0 then
        addImportRequest(requests, payload.hero, "hero")
    end

    for _, entry in ipairs(payload.cards) do
        addImportRequest(requests, entry, "mainboard")
    end

    return requests
end

function addImportRequest(requests, entry, fallback_role)
    local quantity = math.floor(tonumber(entry.quantity or 0) or 0)
    local name = trim(entry.name or "")
    local card_id = trim(entry.card_id or "")
    if quantity <= 0 or name == "" then
        return
    end

    local role = tostring(entry.role or fallback_role)
    local identity_key = card_id ~= "" and card_id or normalizeLookupValue(name)
    local key = role .. "\n" .. identity_key
    local existing = requests.by_key ~= nil and requests.by_key[key] or nil
    if existing ~= nil then
        existing.quantity = existing.quantity + quantity
        existing.remaining = existing.remaining + quantity
        return
    end

    local request = {
        role = role,
        quantity = quantity,
        remaining = quantity,
        name = name,
        card_id = card_id,
        source_resolved = false,
        source = nil,
    }
    table.insert(requests, request)

    requests.by_key = requests.by_key or {}
    requests.by_key[key] = request
end

function countRequestedCards(requests)
    local total = 0
    for _, request in ipairs(requests) do
        total = total + request.quantity
    end
    return total
end

function buildSearchIndex(region_guids)
    local search_index = createSearchIndex()

    for _, guid in ipairs(region_guids) do
        local region = getObjectFromGUID(guid)
        if isScriptingRegion(region) then
            for _, object in ipairs(region.getObjects()) do
                addObjectToSearchIndex(search_index, object)
            end
        end
    end

    return search_index
end

function createSearchIndex()
    return {
        entries = {},
        by_card_id = {},
        card_id_counts = {},
        by_name = {},
        name_counts = {},
    }
end

function addSearchIndexEntry(search_index, contained)
    local metadata = readSourceMetadata(contained)
    local row = {
        data = contained,
        name = metadata.name,
        card_id = metadata.card_id,
    }

    table.insert(search_index.entries, row)

    if row.card_id ~= nil and row.card_id ~= "" then
        search_index.card_id_counts[row.card_id] = (search_index.card_id_counts[row.card_id] or 0) + 1
        if search_index.by_card_id[row.card_id] == nil then
            search_index.by_card_id[row.card_id] = row
        end
    end
    if row.name ~= nil and row.name ~= "" then
        local normalized_name = normalizeLookupValue(row.name)
        search_index.name_counts[normalized_name] = (search_index.name_counts[normalized_name] or 0) + 1
        if search_index.by_name[normalized_name] == nil then
            search_index.by_name[normalized_name] = row
        end
    end
end

function addObjectToSearchIndex(search_index, object)
    if object == nil or object.isDestroyed() then
        return
    end

    local data = object.getData()
    local contained_objects = data.ContainedObjects or {}

    if #contained_objects > 0 then
        for _, contained in ipairs(contained_objects) do
            addSearchIndexEntry(search_index, contained)
        end
        return
    end

    addSearchIndexEntry(search_index, data)
end

function startCardReaderLibraryScan(job, payload)
    local target_region_guid = nil
    for _, guid in ipairs(CONFIG.source_region_guids) do
        if isScriptingRegion(getObjectFromGUID(guid)) then
            target_region_guid = guid
            break
        end
    end
    if target_region_guid == nil then
        failCardReaderLibrarySync(job, "no configured source scripting region was found")
        return
    end

    job.payload = payload
    job.search_index = createSearchIndex()
    job.target_region_guid = target_region_guid
    job.target_batch_count = 0
    job.region_index = 1
    job.current_region_guid = nil
    job.region_objects = nil
    job.region_object_index = 1
    job.contained_objects = nil
    job.contained_index = 1
    scanCardReaderLibraryBatch(job)
end

function scanCardReaderLibraryBatch(job)
    if not librarySyncJobIsCurrent(job) then
        return
    end

    local processed = 0
    while processed < CONFIG.index_batch_size do
        if job.contained_objects ~= nil then
            local contained = job.contained_objects[job.contained_index]
            if contained == nil then
                job.contained_objects = nil
                job.region_object_index = job.region_object_index + 1
            else
                addSearchIndexEntry(job.search_index, contained)
                job.contained_index = job.contained_index + 1
                processed = processed + 1
            end
        elseif job.region_objects == nil then
            local guid = CONFIG.source_region_guids[job.region_index]
            if guid == nil then
                finishCardReaderLibraryScan(job)
                return
            end

            local region = getObjectFromGUID(guid)
            if not isScriptingRegion(region) then
                job.region_index = job.region_index + 1
            else
                job.current_region_guid = guid
                job.region_objects = region.getObjects()
                job.region_object_index = 1
            end
        else
            local object = job.region_objects[job.region_object_index]
            if object == nil then
                job.region_objects = nil
                job.current_region_guid = nil
                job.region_index = job.region_index + 1
            elseif object.isDestroyed() then
                job.region_object_index = job.region_object_index + 1
                processed = processed + 1
            elseif object.tag == "Deck" then
                if job.current_region_guid == job.target_region_guid then
                    job.target_batch_count = job.target_batch_count + 1
                end
                job.contained_objects = object.getObjects()
                job.contained_index = 1
                if #job.contained_objects == 0 then
                    job.contained_objects = nil
                    job.region_object_index = job.region_object_index + 1
                    processed = processed + 1
                end
            elseif object.tag == "Card" then
                if job.current_region_guid == job.target_region_guid then
                    job.target_batch_count = job.target_batch_count + 1
                end
                addSearchIndexEntry(job.search_index, {
                    Name = object.getName(),
                    Description = object.getDescription(),
                    GMNotes = object.getGMNotes(),
                })
                job.region_object_index = job.region_object_index + 1
                processed = processed + 1
            else
                job.region_object_index = job.region_object_index + 1
                processed = processed + 1
            end
        end
    end

    Wait.frames(function()
        scanCardReaderLibraryBatch(job)
    end, 1)
end

function finishCardReaderLibraryScan(job)
    if not librarySyncJobIsCurrent(job) then
        return
    end

    local missing_cards = {}
    local existing_count = 0
    local legacy_count = 0
    for _, card in ipairs(job.payload.cards) do
        local card_id = trim(card.card_id or "")
        local existing = job.search_index.by_card_id[card_id]
        if existing ~= nil then
            existing_count = existing_count + 1
        else
            local normalized_name = normalizeLookupValue(card.name or "")
            local legacy = job.search_index.by_name[normalized_name]
            if job.search_index.name_counts[normalized_name] == 1
                and legacy ~= nil
                and (legacy.card_id == nil or legacy.card_id == "") then
                legacy_count = legacy_count + 1
            else
                table.insert(missing_cards, card)
            end
        end
    end

    local duplicate_count = countDuplicateCardReaderIds(job.search_index)
    local skipped_count = #(job.payload.skipped or {})
    if #missing_cards == 0 then
        printCardReaderLibrarySyncSummary(
            existing_count,
            0,
            legacy_count,
            duplicate_count,
            skipped_count
        )
        finishCardReaderLibrarySync(job)
        return
    end

    local update_payload = buildCardReaderLibraryUpdatePayload(job.payload, missing_cards)
    local position = buildCardReaderLibraryBatchPosition(job.target_batch_count)
    spawnCardReaderSheetDeck(update_payload, {
        position = position,
        callback_function = function(object, spawned_count)
            if object == nil or object.isDestroyed() then
                failCardReaderLibrarySync(job, "the missing-card batch failed to spawn")
                return
            end
            printCardReaderLibrarySyncSummary(
                existing_count,
                spawned_count,
                legacy_count,
                duplicate_count,
                skipped_count
            )
            finishCardReaderLibrarySync(job)
        end,
    })
end

function buildCardReaderLibraryUpdatePayload(payload, missing_cards)
    local required_sheet_ids = {}
    for _, card in ipairs(missing_cards) do
        required_sheet_ids[card.sheet_id] = true
    end

    local sheets = {}
    for _, sheet in ipairs(payload.sheets) do
        if required_sheet_ids[sheet.sheet_id] then
            table.insert(sheets, sheet)
        end
    end

    return {
        schema = payload.schema,
        collection = {
            name = string.format("Card Reader Library Update (%d new)", #missing_cards),
            source = payload.collection.source,
        },
        card_back_url = payload.card_back_url,
        sheets = sheets,
        cards = missing_cards,
        skipped = {},
    }
end

function buildCardReaderLibraryBatchPosition(existing_batch_count)
    return {
        x = CONFIG.spawn_position.x + (existing_batch_count * CONFIG.library_batch_spacing),
        y = CONFIG.spawn_position.y,
        z = CONFIG.spawn_position.z,
    }
end

function countDuplicateCardReaderIds(search_index)
    local duplicate_count = 0
    for _, count in pairs(search_index.card_id_counts) do
        if count > 1 then
            duplicate_count = duplicate_count + count - 1
        end
    end
    return duplicate_count
end

function printCardReaderLibrarySyncSummary(existing, added, legacy, duplicates, skipped)
    print(string.format(
        "Card Reader library sync complete: existing=%d, added=%d, legacy-matched=%d, duplicates=%d, server-skipped=%d.",
        existing,
        added,
        legacy,
        duplicates,
        skipped
    ))
end

function startImportJob(payload, requests)
    local job = createImportJob(payload, requests)
    job.search_index = createSearchIndex()
    job.source_region_guids = CONFIG.source_region_guids
    job.region_index = 1
    job.region_objects = nil
    job.region_object_index = 1
    job.contained_objects = nil
    job.contained_index = 1

    print(string.format(
        "Importing '%s' with %d card types and %d requested cards.",
        payloadCollectionName(payload),
        #requests,
        countRequestedCards(requests)
    ))
    buildSearchIndexForImport(job)
end

function createImportJob(payload, requests)
    return {
        payload = payload,
        requests = requests,
        request_index = 1,
        spawn_index = 1,
        expected_spawns = 0,
        spawned = {},
        missing = {},
    }
end

function buildExportSkippedRequests(skipped)
    local requests = {}
    for _, entry in ipairs(skipped or {}) do
        table.insert(requests, {
            quantity = 1,
            name = trim(entry.name or entry.card_id or "Unknown card"),
            role = "export",
            reason = trim(entry.reason or "Skipped by Card Reader."),
        })
    end
    return requests
end

function buildSearchIndexForImport(job)
    local processed = 0

    while processed < CONFIG.index_batch_size do
        if job.contained_objects ~= nil then
            local contained = job.contained_objects[job.contained_index]
            if contained == nil then
                job.contained_objects = nil
                job.region_object_index = job.region_object_index + 1
            else
                addSearchIndexEntry(job.search_index, contained)
                job.contained_index = job.contained_index + 1
                processed = processed + 1
            end
        elseif job.region_objects == nil then
            local guid = job.source_region_guids[job.region_index]
            if guid == nil then
                print(string.format("Indexed %d source cards.", #job.search_index.entries))
                spawnImportBatch(job)
                return
            end

            local region = getObjectFromGUID(guid)
            if region == nil then
                print("Source scripting region not found: " .. tostring(guid))
                job.region_index = job.region_index + 1
            elseif not isScriptingRegion(region) then
                print("Source GUID is not a scripting region: " .. tostring(guid))
                job.region_index = job.region_index + 1
            else
                job.region_objects = region.getObjects()
                job.region_object_index = 1
            end
        else
            local object = job.region_objects[job.region_object_index]
            if object == nil then
                job.region_objects = nil
                job.region_index = job.region_index + 1
            elseif object.isDestroyed() then
                job.region_object_index = job.region_object_index + 1
            else
                local data = object.getData()
                local contained_objects = data.ContainedObjects or {}
                if #contained_objects > 0 then
                    job.contained_objects = contained_objects
                    job.contained_index = 1
                else
                    addSearchIndexEntry(job.search_index, data)
                    job.region_object_index = job.region_object_index + 1
                    processed = processed + 1
                end
            end
        end
    end

    Wait.frames(function()
        buildSearchIndexForImport(job)
    end, 1)
end

function isScriptingRegion(object)
    return object ~= nil and type(object.getObjects) == "function"
end

function spawnImportBatch(job)
    local processed = 0

    while processed < CONFIG.spawn_batch_size do
        local request = job.requests[job.request_index]
        if request == nil then
            waitForImportSpawns(job)
            return
        end

        if request.remaining <= 0 then
            job.request_index = job.request_index + 1
        else
            if not request.source_resolved then
                request.source = findSourceCard(request, job.search_index)
                request.source_resolved = true
            end

            if request.source == nil then
                table.insert(job.missing, request)
                job.request_index = job.request_index + 1
                processed = processed + 1
            else
                spawnImportCard(job, request)
                request.remaining = request.remaining - 1
                processed = processed + 1
                if request.remaining <= 0 then
                    job.request_index = job.request_index + 1
                end
            end
        end
    end

    Wait.frames(function()
        spawnImportBatch(job)
    end, 1)
end

function spawnImportCard(job, request)
    local spawn_position = buildSpawnPosition(job.spawn_index)
    local object_data = deepCopy(request.source.data)
    object_data.GUID = nil
    job.expected_spawns = job.expected_spawns + 1
    job.spawn_index = job.spawn_index + 1

    spawnObjectData({
        data = object_data,
        position = spawn_position,
        callback_function = function(spawned_object)
            applySpawnMetadata(spawned_object, request)
            table.insert(job.spawned, spawned_object)
        end,
    })
end

function verifiedAssetUrl(url)
    local prefix = "{verifycache}"
    if string.sub(url, 1, #prefix) == prefix then
        return url
    end
    return prefix .. url
end

function countMissingCards(missing)
    local total = 0
    for _, request in ipairs(missing or {}) do
        total = total + (tonumber(request.quantity or 0) or 0)
    end
    return total
end

function waitForImportSpawns(job)
    logMissingCards(job.missing)

    if job.expected_spawns == 0 then
        finalizeImportedDeck(job.payload, job.spawned, job.missing)
        return
    end

    Wait.condition(
        function()
            scheduleFinalizeImportedDeck(job)
        end,
        function()
            return #job.spawned == job.expected_spawns
        end,
        CONFIG.wait_timeout_seconds,
        function()
            print(string.format(
                "Timed out while waiting for imported cards to finish spawning. Spawned %d of %d found cards.",
                #job.spawned,
                job.expected_spawns
            ))
            logMissingCards(job.missing)
            scheduleFinalizeImportedDeck(job)
        end
    )
end

function readSourceMetadata(card_data)
    local gm_notes = card_data.GMNotes or card_data.gm_notes or ""
    local description = card_data.Description or card_data.description or ""
    local nickname = trim(card_data.Nickname or card_data.nickname or card_data.Name or card_data.name or "")
    local metadata = {
        name = nickname,
        card_id = nil,
    }

    local parsed = decodeEmbeddedJson(gm_notes) or decodeEmbeddedJson(description)
    if parsed ~= nil then
        metadata.name = parsed.name or metadata.name
        if type(parsed.card_id) == "string" and trim(parsed.card_id) ~= "" then
            metadata.card_id = trim(parsed.card_id)
        end
    end

    return metadata
end

function findSourceCard(request, search_index)
    if request.card_id ~= nil and request.card_id ~= "" then
        local card_id_match = search_index.by_card_id[request.card_id]
        if card_id_match ~= nil then
            return card_id_match
        end
    end
    if request.name == nil or request.name == "" then
        return nil
    end

    local normalized = normalizeLookupValue(request.name)
    if search_index.by_name[normalized] ~= nil then
        return search_index.by_name[normalized]
    end

    return findFuzzyNameSource(normalized, search_index)
end

function findFuzzyNameSource(normalized_name, search_index)
    local match = nil
    local match_count = 0

    for _, entry in ipairs(search_index.entries) do
        if entry.name ~= nil and namesAreWithinDistance(normalized_name, normalizeLookupValue(entry.name), CONFIG.fuzzy_name_distance) then
            match = entry
            match_count = match_count + 1
            if match_count > 1 then
                return nil
            end
        end
    end

    return match
end

function namesAreWithinDistance(left, right, max_distance)
    local left_length = #left
    local right_length = #right
    local length_delta = math.abs(left_length - right_length)

    if length_delta > max_distance then
        return false
    end

    if left_length == right_length then
        local differences = 0
        for index = 1, left_length do
            if string.sub(left, index, index) ~= string.sub(right, index, index) then
                differences = differences + 1
                if differences > max_distance then
                    return false
                end
            end
        end
        return true
    end

    return namesMatchWithOneInsertionOrDeletion(left, right)
end

function namesMatchWithOneInsertionOrDeletion(left, right)
    local shorter = left
    local longer = right

    if #left > #right then
        shorter = right
        longer = left
    end

    local shorter_index = 1
    local longer_index = 1
    local skipped = 0

    while shorter_index <= #shorter and longer_index <= #longer do
        if string.sub(shorter, shorter_index, shorter_index) == string.sub(longer, longer_index, longer_index) then
            shorter_index = shorter_index + 1
            longer_index = longer_index + 1
        else
            skipped = skipped + 1
            if skipped > 1 then
                return false
            end
            longer_index = longer_index + 1
        end
    end

    return true
end

function buildSpawnPosition(index)
    local zero_based = index - 1

    return {
        x = CONFIG.spawn_position.x,
        y = CONFIG.spawn_position.y + (zero_based * CONFIG.stack_y_spacing),
        z = CONFIG.spawn_position.z,
    }
end

function scheduleFinalizeImportedDeck(job)
    Wait.frames(function()
        finalizeImportedDeck(job.payload, job.spawned, job.missing)
    end, CONFIG.finalize_wait_frames)
end

function finalizeImportedDeck(payload, objects, missing)
    local primary = findImportedDeckTarget(objects)
    local collection_name = payloadCollectionName(payload)

    if primary == nil and #objects == 0 then
        print("No cards were spawned.")
        return
    end

    if primary ~= nil and not primary.isDestroyed() then
        primary.setName(collection_name)
        local description = payloadDescription(payload)
        if description ~= nil then
            primary.setDescription(description)
        end
    else
        print("Imported deck target could not be found for naming.")
    end

    local missing_count = countMissingCards(missing)
    if missing_count > 0 then
        print(string.format(
            "Imported '%s' with %d spawned cards and %d missing cards.",
            collection_name,
            #objects,
            missing_count
        ))
    else
        print(string.format("Imported '%s' with %d spawned cards.", collection_name, #objects))
    end
end

function payloadCollectionName(payload)
    if type(payload.deck) == "table" then
        return payload.deck.name
    end
    return payload.collection.name
end

function payloadDescription(payload)
    if type(payload.deck) == "table" then
        return payload.deck.description
    end
    return nil
end

function findImportedDeckTarget(objects)
    local live_objects = collectLiveObjects(objects)
    if #live_objects > 1 then
        local grouped = group(live_objects) or {}
        return grouped[1] or live_objects[1]
    end

    if #live_objects == 1 then
        return live_objects[1]
    end

    return findNearestSpawnedObject()
end

function collectLiveObjects(objects)
    local live_objects = {}

    for _, object in ipairs(objects or {}) do
        if object ~= nil and not object.isDestroyed() then
            table.insert(live_objects, object)
        end
    end

    return live_objects
end

function findNearestSpawnedObject()
    local nearest = nil
    local nearest_distance = nil

    for _, object in ipairs(getAllObjects()) do
        if isImportDeckTargetCandidate(object) then
            local position = object.getPosition()
            local distance = horizontalDistance(position, CONFIG.spawn_position)

            if distance <= CONFIG.finalize_search_radius
                and (nearest_distance == nil or distance < nearest_distance) then
                nearest = object
                nearest_distance = distance
            end
        end
    end

    return nearest
end

function isImportDeckTargetCandidate(object)
    if object == nil or object.isDestroyed() then
        return false
    end

    return object.tag == "Card" or object.tag == "Deck"
end

function horizontalDistance(left, right)
    local dx = left.x - right.x
    local dz = left.z - right.z

    return math.sqrt((dx * dx) + (dz * dz))
end

function logMissingCards(missing)
    if missing == nil or #missing == 0 then
        return
    end

    local rows = {}
    for index, request in ipairs(missing) do
        local row = string.format(
            "%d. %s x%d | role=%s",
            index,
            tostring(request.name or "-"),
            tonumber(request.quantity or 0) or 0,
            tostring(request.role or "-")
        )
        if request.reason ~= nil and request.reason ~= "" then
            row = row .. " | reason=" .. tostring(request.reason)
        end
        table.insert(rows, row)
    end

    print("Skipped or missing Card Reader cards:\n" .. table.concat(rows, "\n"))
end

function applySpawnMetadata(object, request)
    if request.name ~= nil and request.name ~= "" then
        object.setName(request.name)
    end
end

function decodeEmbeddedJson(text)
    if type(text) ~= "string" or trim(text) == "" then
        return nil
    end

    local ok, parsed = pcall(JSON.decode, text)
    if ok and type(parsed) == "table" then
        return parsed
    end

    return nil
end

function normalizeLookupValue(value)
    return string.lower(trim(tostring(value)))
end

function trim(value)
    if type(value) ~= "string" or value == "" then
        return ""
    end

    local first = 1
    local last = #value

    while first <= last and isWhitespace(string.sub(value, first, first)) do
        first = first + 1
    end

    while last >= first and isWhitespace(string.sub(value, last, last)) do
        last = last - 1
    end

    return string.sub(value, first, last)
end

function isWhitespace(character)
    return character == " " or character == "\t" or character == "\r" or character == "\n"
end

function deepCopy(value)
    if type(value) ~= "table" then
        return value
    end

    local result = {}
    for key, item in pairs(value) do
        result[key] = deepCopy(item)
    end
    return result
end

local BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
local BASE64_VALUES = {}
local BASE64_OUTPUT_CHUNK_SIZE = 1024

for index = 1, #BASE64_ALPHABET do
    BASE64_VALUES[string.sub(BASE64_ALPHABET, index, index)] = index - 1
end

function base64Decode(input)
    if type(input) ~= "string" then
        error("Base64 input must be a string.")
    end

    local clean = string.gsub(input, "%s", "")
    if #clean == 0 or #clean % 4 ~= 0 then
        error("Invalid base64 input length.")
    end

    local output = {}
    local output_chunk = {}

    for index = 1, #clean, 4 do
        local character1 = string.sub(clean, index, index)
        local character2 = string.sub(clean, index + 1, index + 1)
        local character3 = string.sub(clean, index + 2, index + 2)
        local character4 = string.sub(clean, index + 3, index + 3)
        local is_last_group = index + 3 == #clean

        if character1 == "="
            or character2 == "="
            or (character3 == "=" and character4 ~= "=")
            or ((character3 == "=" or character4 == "=") and not is_last_group) then
            error("Invalid base64 padding near position " .. tostring(index) .. ".")
        end

        local value1 = BASE64_VALUES[character1]
        local value2 = BASE64_VALUES[character2]
        local value3 = character3 == "=" and 0 or BASE64_VALUES[character3]
        local value4 = character4 == "=" and 0 or BASE64_VALUES[character4]
        if value1 == nil or value2 == nil or value3 == nil or value4 == nil then
            error("Invalid base64 character near position " .. tostring(index) .. ".")
        end

        local byte1 = (value1 * 4) + math.floor(value2 / 16)
        local byte2 = ((value2 % 16) * 16) + math.floor(value3 / 4)
        local byte3 = ((value3 % 4) * 64) + value4

        if character3 == "=" then
            output_chunk[#output_chunk + 1] = string.char(byte1)
        elseif character4 == "=" then
            output_chunk[#output_chunk + 1] = string.char(byte1, byte2)
        else
            output_chunk[#output_chunk + 1] = string.char(byte1, byte2, byte3)
        end

        if #output_chunk >= BASE64_OUTPUT_CHUNK_SIZE then
            output[#output + 1] = table.concat(output_chunk)
            output_chunk = {}
        end
    end

    if #output_chunk > 0 then
        output[#output + 1] = table.concat(output_chunk)
    end

    return table.concat(output)
end
