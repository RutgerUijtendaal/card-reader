local CONFIG = {
    -- World position used for Card Reader imports triggered by players.
    spawn_position = { x = -45, y = 3, z = 50 },
}

local import_string = ""

function input_func(obj, color, input, still_editing)
    import_string = input or ""
end

function onLoad()
    self.createInput({
        input_function = "input_func",
        function_owner = self,
        label = "Import String",
        alignment = 3,
        position = { x = 0, y = 0.2, z = -0.5 },
        width = 1000,
        height = 200,
        value = import_string,
    })
    self.createButton({
        click_function = "click_import",
        function_owner = self,
        label = "Import",
        position = { 0, 0.2, 0.30 },
        width = 1200,
        height = 300,
        font_size = 100,
        color = { 0.5, 0.5, 1 },
        font_color = { 1, 1, 1 },
        tooltip = "Import a Card Reader export",
    })
end

function click_import(obj, color, alt_click)
    importCardReaderExport(import_string)
end

function importCardReaderExport(encoded)
    local payload = decodePayload(encoded)
    validateExportPayload(payload)
    spawnCardReaderSheetDeck(payload)
end

function decodePayload(encoded)
    local ok, json_text = pcall(base64Decode, encoded)
    if not ok then
        error("Failed to decode base64 payload: " .. tostring(json_text))
    end

    return JSON.decode(json_text)
end

function validateExportPayload(payload)
    if type(payload) ~= "table" then
        error("Decoded payload must be a table.")
    end

    if payload.schema == "card-reader.tts-deck.v1"
        or payload.schema == "card-reader.tts-cards.v1" then
        error("This export is outdated. Re-export it from Card Reader to use sheet-based cards.")
    end
    if payload.schema ~= "card-reader.tts-cards.v2" then
        error("Unsupported payload schema: " .. tostring(payload.schema))
    end

    if type(payload.collection) ~= "table"
        or type(payload.collection.name) ~= "string"
        or trim(payload.collection.name) == "" then
        error("Payload collection metadata is invalid.")
    end
    if payload.collection.description ~= nil
        and type(payload.collection.description) ~= "string" then
        error("Payload collection description is invalid.")
    end
    if payload.collection.source ~= nil and type(payload.collection.source) ~= "table" then
        error("Payload collection source is invalid.")
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
            or math.floor(tonumber(entry.quantity or 0) or 0) <= 0
            or (entry.role ~= nil and type(entry.role) ~= "string") then
            error("Payload card entry " .. tostring(index) .. " is invalid.")
        end
    end

    if payload.skipped ~= nil and type(payload.skipped) ~= "table" then
        error("Payload skipped collection is invalid.")
    end
end

function spawnCardReaderSheetDeck(payload)
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
            table.insert(contained, buildSheetContainedCardData(
                entry,
                card_id,
                payload.sheets[sheet_key].face_url
            ))
        end
    end

    logSkippedCards(payload.skipped)
    local object_data
    if #contained == 1 then
        object_data = buildStandaloneSheetCardData(
            contained[1],
            custom_deck,
            payload.collection
        )
    else
        object_data = buildSheetDeckData(
            payload.collection,
            deck_ids,
            custom_deck,
            contained
        )
    end

    spawnObjectData({
        data = object_data,
        position = CONFIG.spawn_position,
        callback_function = function(object)
            if object ~= nil and not object.isDestroyed() then
                print(string.format(
                    "Imported '%s' with %d cards across %d sheets.",
                    payload.collection.name,
                    #contained,
                    #payload.sheets
                ))
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

function buildSheetContainedCardData(entry, card_id, sheet_url)
    local metadata = {
        schema = "card-reader.tts-card.v2",
        card_id = trim(entry.card_id),
        card_version_id = trim(entry.card_version_id),
        name = trim(entry.name),
        image_checksum = trim(entry.image_checksum or ""),
        sheet_id = trim(entry.sheet_id),
        slot_index = math.floor(tonumber(entry.slot_index)),
        stable_sheet_url = trim(sheet_url),
        lifecycle_status = trim(entry.lifecycle_status or ""),
    }
    if type(entry.role) == "string" and trim(entry.role) ~= "" then
        metadata.role = trim(entry.role)
    end

    return {
        Name = "Card",
        Transform = defaultObjectTransform(),
        Nickname = trim(entry.name),
        Description = "",
        GMNotes = JSON.encode(metadata),
        CardID = card_id,
        SidewaysCard = false,
        LuaScript = "",
        LuaScriptState = "",
        XmlUI = "",
    }
end

function buildStandaloneSheetCardData(contained_card, custom_deck, collection)
    local object_data = deepCopy(contained_card)
    local sheet_key = math.floor(tonumber(object_data.CardID) / 100)
    object_data.Name = "CardCustom"
    object_data.CustomDeck = {
        [sheet_key] = custom_deck[sheet_key],
    }

    if collectionIsDeck(collection) then
        object_data.Nickname = trim(collection.name)
        object_data.Description = collectionDescription(collection)
        local metadata = JSON.decode(object_data.GMNotes)
        metadata.collection = collection
        object_data.GMNotes = JSON.encode(metadata)
    end
    return object_data
end

function buildSheetDeckData(collection, deck_ids, custom_deck, contained)
    return {
        Name = "DeckCustom",
        Transform = defaultObjectTransform(),
        Nickname = trim(collection.name),
        Description = collectionDescription(collection),
        GMNotes = JSON.encode({
            schema = "card-reader.tts-collection.v1",
            collection = collection,
        }),
        DeckIDs = deck_ids,
        CustomDeck = custom_deck,
        ContainedObjects = contained,
        LuaScript = "",
        LuaScriptState = "",
        XmlUI = "",
    }
end

function collectionIsDeck(collection)
    return type(collection.source) == "table" and collection.source.type == "deck"
end

function collectionDescription(collection)
    if type(collection.description) == "string" then
        return collection.description
    end
    return ""
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

function verifiedAssetUrl(url)
    local prefix = "{verifycache}"
    if string.sub(url, 1, #prefix) == prefix then
        return url
    end
    return prefix .. url
end

function logSkippedCards(skipped)
    if skipped == nil or #skipped == 0 then
        return
    end

    local rows = {}
    for index, entry in ipairs(skipped) do
        local quantity = math.floor(tonumber(entry.quantity or 1) or 1)
        local row = string.format(
            "%d. %s x%d | role=%s",
            index,
            tostring(entry.name or entry.card_id or "Unknown card"),
            quantity,
            tostring(entry.role or "export")
        )
        if entry.reason ~= nil and entry.reason ~= "" then
            row = row .. " | reason=" .. tostring(entry.reason)
        end
        table.insert(rows, row)
    end

    print("Skipped Card Reader cards:\n" .. table.concat(rows, "\n"))
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
